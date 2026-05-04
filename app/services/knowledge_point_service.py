"""知识点服务 - 批量知识点匹配"""

import json
import re
import logging
from typing import List, Dict, Any

# 获取知识点评测专用日志记录器
kp_logger = logging.getLogger("knowledge_point")


class KnowledgePointService:
    """知识点业务逻辑 - 批量处理"""

    @staticmethod
    async def match_and_assign_knowledge_points(
        questions: List[Dict],
        subject_id: int,
        level_id: int,
        llm_service
    ) -> Dict[str, Any]:
        """批量匹配知识点（一次API调用完成所有题目）

        Args:
            questions: 题目列表，每项包含 id, content
            subject_id: 科目ID
            level_id: 等级ID
            llm_service: LLM服务实例

        Returns:
            匹配结果，包含 summary 和 results
        """
        from app.models.knowledge_point import KnowledgePoint

        # 获取该科目等级下的现有知识点
        existing_kps = await KnowledgePoint.filter(subject_id=subject_id, level_id=level_id).all()
        kp_map = {kp.name: kp for kp in existing_kps}
        kp_logger.debug(f"现有知识点数量: {len(existing_kps)}, 科目ID: {subject_id}, 等级ID: {level_id}")

        results = []
        summary = {"total": len(questions), "assigned": 0, "created": 0, "no_match": 0}

        # 构建批量prompt
        questions_data = []
        for q in questions:
            content = q.get('content', '')[:300] if q.get('content') else ""
            if not content.strip():
                continue
            questions_data.append({
                "id": q.get('id'),
                "content": content
            })

        if not questions_data:
            kp_logger.warning("没有有效的题目数据")
            return {"results": results, "summary": summary}

        # 构建知识点列表（包含关键词）
        kp_list_str = "\n".join([
            f"- {kp.name}" + (f" (关键词: {kp.keywords})" if kp.keywords else "")
            for kp in existing_kps
        ]) if existing_kps else "（暂无知识点，将根据题目内容自动创建）"

        # 构建题目列表
        questions_str = "\n".join([
            f"题目{idx+1} [ID:{q['id']}]：{q['content']}"
            for idx, q in enumerate(questions_data)
        ])

        prompt = f"""你需要为以下 {len(questions_data)} 道题目匹配知识点。

现有知识点列表：
{kp_list_str}

需要匹配的题目：
{questions_str}

请根据每道题目的内容，匹配到最合适的知识点（一道题可以匹配多个知识点，用逗号分隔）。如果现有知识点都不合适，请在知识点名称前加"新建:"前缀创建新知识点。

重要：请直接返回JSON数组，不要任何其他文字内容，不要用markdown包裹：
[{{"question_id":1,"knowledge_points":"知识点1,知识点2","reason":"匹配理由"}},{{"question_id":2,"knowledge_points":"新建:新知识点","reason":"理由"}}]"""

        try:
            messages = [
                {'role': 'system', 'content': '你是一个专业的知识点分类助手。请根据题目内容，从给定的知识点列表中选择最匹配的（一道题可以匹配多个知识点），或建议创建新知识点。'},
                {'role': 'user', 'content': prompt}
            ]
            kp_logger.info(f"开始调用AI匹配知识点，题目数量: {len(questions_data)}")
            response = llm_service.provider_instance.chat_completion(messages)
            kp_logger.debug(f"AI响应长度: {len(response)}, 响应前500字符: {response[:500]}")

            # 提取JSON数组
            ai_results = KnowledgePointService._parse_ai_response(response)
            if not ai_results:
                kp_logger.warning("无法从AI响应中提取有效的JSON结果")
                return {"results": results, "summary": summary}

            ai_result_map = {r.get('question_id'): r for r in ai_results}
            kp_logger.info(f"AI返回的知识点匹配结果数量: {len(ai_result_map)}")

            # 需要创建的新知识点
            new_kp_names = set()

            # 第一遍：收集需要创建的新知识点，并更新kp_map
            for q_data in questions_data:
                ai_result = ai_result_map.get(q_data['id'], {})
                if not ai_result:
                    kp_logger.debug(f"题目ID {q_data['id']} 没有AI匹配结果")
                    continue

                kp_names_str = ai_result.get("knowledge_points", "")
                if not kp_names_str:
                    continue

                # 解析多个知识点
                for kp_name in kp_names_str.split(","):
                    kp_name = kp_name.strip()
                    clean_name = kp_name
                    if kp_name.startswith("新建:"):
                        clean_name = kp_name[3:].strip()
                        if clean_name:
                            new_kp_names.add(clean_name)
                            kp_logger.debug(f"题目ID {q_data['id']} 需要创建新知识点: {clean_name}")
                    elif kp_name:
                        if kp_name not in kp_map:
                            new_kp_names.add(kp_name)
                            kp_logger.debug(f"题目ID {q_data['id']} 需要创建知识点: {kp_name} (不在现有列表中)")

            kp_logger.info(f"需要创建的新知识点数量: {len(new_kp_names)}")

            # 批量创建新知识点
            for new_name in new_kp_names:
                kp = await KnowledgePointService.get_or_create_knowledge_point(
                    subject_id=subject_id,
                    level_id=level_id,
                    name=new_name,
                    description="自动创建"
                )
                kp_map[new_name] = kp
                kp_logger.debug(f"已创建知识点: {new_name}")

            # 第二遍：分配知识点到题目
            for q_data in questions_data:
                q_id = q_data['id']
                ai_result = ai_result_map.get(q_id, {})
                kp_ids = []
                kp_names = []

                if ai_result:
                    kp_names_str = ai_result.get("knowledge_points", "")
                    for kp_name in kp_names_str.split(","):
                        original_kp_name = kp_name.strip()
                        clean_kp_name = original_kp_name
                        if original_kp_name.startswith("新建:"):
                            clean_kp_name = original_kp_name[3:].strip()

                        if clean_kp_name and clean_kp_name in kp_map:
                            kp = kp_map[clean_kp_name]
                            kp_ids.append(kp.id)
                            kp_names.append(kp.name)

                if kp_ids:
                    results.append({
                        "question_id": q_id,
                        "knowledge_point_ids": kp_ids,
                        "knowledge_point_names": kp_names,
                        "status": "assigned"
                    })
                    summary["assigned"] += 1
                else:
                    results.append({
                        "question_id": q_id,
                        "knowledge_point_ids": [],
                        "knowledge_point_names": [],
                        "status": "no_match"
                    })
                    summary["no_match"] += 1

            # 统计创建的新知识点数量
            summary["created"] = len(new_kp_names)
            kp_logger.info(f"知识点匹配完成: 分配{summary['assigned']}个, 新建{summary['created']}个, 未匹配{summary['no_match']}个")

        except Exception as e:
            kp_logger.exception(f"知识点匹配过程发生异常: {str(e)}")
            return {"results": [], "summary": {**summary, "error": str(e)}}

        return {"results": results, "summary": summary}

    @staticmethod
    def _parse_ai_response(response: str) -> List[Dict]:
        """解析AI返回的JSON响应"""
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 块
        json_match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试提取数组模式
        json_match = re.search(r'(\[\s*\{[\s\S]*?\}\s*\]\s*)', response)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        return []

    @staticmethod
    async def get_or_create_knowledge_point(
        subject_id: int,
        level_id: int,
        name: str,
        description: str = None,
        keywords: str = None
    ) -> "KnowledgePoint":
        """获取或创建知识点（如果不存在则创建）"""
        from app.models.knowledge_point import KnowledgePoint
        kp = await KnowledgePoint.get_or_none(name=name, subject_id=subject_id)
        if not kp:
            kp = await KnowledgePoint.create(
                name=name,
                subject_id=subject_id,
                level_id=level_id,
                description=description,
                keywords=keywords
            )
            kp_logger.debug(f"创建新知识点: {name}")
        return kp
