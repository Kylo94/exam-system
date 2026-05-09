"""知识点服务 - 批量知识点匹配"""

import json
import logging
import re
from typing import Any, Dict, List

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
        for idx, q in enumerate(questions):
            content = q.get('content', '')[:300] if q.get('content') else ""
            if not content.strip():
                continue
            questions_data.append({
                "id": q.get('id'),  # 实际ID
                "order": idx + 1,   # 序号（从1开始）
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
            f"题目{q['order']}：{q['content']}"
            for q in questions_data
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

            # 使用 order 字段作为 key（AI返回的是序号）
            ai_result_map = {r.get('question_id'): r for r in ai_results}
            # 预留：建立 id -> result 的映射用于调试
            # _id_result_map = {q['id']: ai_result_map.get(q['order']) for q in questions_data}
            kp_logger.info(f"AI返回的知识点匹配结果数量: {len(ai_result_map)}, 问题数量: {len(questions_data)}")

            # 需要创建的新知识点
            new_kp_names = set()

            # 第一遍：收集需要创建的新知识点，并更新kp_map
            for q_data in questions_data:
                # 使用 order 来匹配 AI 返回的结果
                ai_result = ai_result_map.get(q_data['order'], {})
                if not ai_result:
                    kp_logger.debug(f"题目序号 {q_data['order']} (ID:{q_data['id']}) 没有AI匹配结果")
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
                            kp_logger.debug(f"题目序号 {q_data['order']} (ID:{q_data['id']}) 需要创建新知识点: {clean_name}")
                    elif kp_name:
                        if kp_name not in kp_map:
                            new_kp_names.add(kp_name)
                            kp_logger.debug(f"题目序号 {q_data['order']} (ID:{q_data['id']}) 需要创建知识点: {kp_name} (不在现有列表中)")

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
                q_order = q_data['order']
                ai_result = ai_result_map.get(q_order, {})
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

        # 尝试提取JSON数组（贪婪匹配，支持跨行）
        json_match = re.search(r'(\[\s*\{[\s\S]+\}\s*\])', response)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试另一种模式：提取所有 {...} 内容并组装成数组
        objects = re.findall(r'\{[^{}]*"question_id"[^{}]*\}', response)
        if objects:
            try:
                # 尝试修复常见格式问题
                fixed = '[' + ','.join(objects) + ']'
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        return []

    @staticmethod
    async def merge_similar_knowledge_points(
        subject_id: int,
        level_id: int,
        llm_service,
        similarity_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """AI合并相似知识点

        Args:
            subject_id: 科目ID
            level_id: 等级ID
            llm_service: LLM服务实例
            similarity_threshold: 相似度阈值（0-1）

        Returns:
            合并结果，包含 merged_count, absorbed_kps, new_kps 等信息
        """
        from app.models.knowledge_point import KnowledgePoint
        from app.models.question import Question

        kp_logger.info(f"开始AI合并知识点，科目ID:{subject_id}, 等级ID:{level_id}")

        # 获取该等级下所有知识点及其题目
        kps = await KnowledgePoint.filter(subject_id=subject_id, level_id=level_id).all()
        if len(kps) < 2:
            return {"merged": 0, "absorbed": [], "new_kps": [], "message": "知识点少于2个，无需合并"}

        # 构建知识点数据（包含题目数量和摘要）
        from app.models.question import Question
        kp_data = []
        for kp in kps:
            questions_count = await Question.filter(knowledge_point_id=kp.id).count()
            kp_data.append({
                "id": kp.id,
                "name": kp.name,
                "description": kp.description or "",
                "keywords": kp.keywords or "",
                "questions_count": questions_count
            })

        # 构建发送给AI的数据
        kp_list_str = "\n".join([
            f"知识点{id}: {kp['name']}" +
            (f" (关键词: {kp['keywords']})" if kp['keywords'] else "") +
            (f" - 包含{kp['questions_count']}道题" if kp['questions_count'] > 0 else " - 无题目")
            for kp in kp_data
        ])

        prompt = f"""你需要分析以下知识点列表，找出可以合并的相似知识点。

知识点列表：
{kp_list_str}

请分析哪些知识点含义相近或重复，可以合并为一个知识点。合并规则：
1. 名称高度相似（如"循环"和"循环结构"）的应合并
2. 关键词重叠较多的应合并
3. 被包含关系（如"Python基础"和"Python数据类型"）可考虑合并
4. 保留名称更准确、题目数量更多的知识点作为主知识点

请返回JSON数组格式，每项表示需要合并的知识点：
[{{"source_names":["知识点A","知识点B"],"target_name":"知识点C","reason":"含义重复，合并到主知识点"}},...]

如果没有发现可合并的知识点，返回空数组 []。

重要：只返回JSON数组，不要任何解释文字，不要用markdown包裹。
"""
        try:
            messages = [
                {'role': 'system', 'content': '你是一个专业的知识点分类助手，擅长发现知识点的相似和重叠关系。'},
                {'role': 'user', 'content': prompt}
            ]

            kp_logger.info(f"调用AI分析知识点合并，知识点数量: {len(kps)}")
            response = llm_service.provider_instance.chat_completion(messages)
            kp_logger.debug(f"AI合并建议响应: {response[:500]}")

            # 解析AI响应
            merge_suggestions = KnowledgePointService._parse_merge_response(response)
            if not merge_suggestions:
                kp_logger.info("AI未返回有效的合并建议")
                return {"merged": 0, "absorbed": [], "new_kps": [], "message": "未发现可合并的相似知识点"}

            kp_logger.info(f"AI建议合并数量: {len(merge_suggestions)}, 建议内容: {merge_suggestions}")

            # 构建名称到KP的映射
            kp_name_map = {kp.name: kp for kp in kps}
            kp_logger.debug(f"知识点名称映射: {list(kp_name_map.keys())}")

            # 执行合并
            merged_count = 0
            absorbed_kps = []
            source_kp_ids = set()

            for suggestion in merge_suggestions:
                source_names = suggestion.get('source_names', [])
                target_name = suggestion.get('target_name')
                if not target_name or not source_names:
                    kp_logger.debug(f"跳过建议: target_name={target_name}, source_names={source_names}")
                    continue

                target_kp = kp_name_map.get(target_name)
                if not target_kp:
                    kp_logger.debug(f"跳过建议: target_name='{target_name}' 未在kps中找到 (kps names: {list(kp_name_map.keys())})")
                    continue
                kp_logger.debug(f"找到target_kp: id={target_kp.id}, name={target_kp.name}")

                for source_name in source_names:
                    if source_name == target_name:
                        continue
                    source_kp = kp_name_map.get(source_name)
                    if not source_kp:
                        kp_logger.debug(f"跳过source_name='{source_name}' (不在kps列表中)")
                        continue

                    # 获取源知识点包含的所有题目（JSON字段不支持__contains，换用全量查询+Python过滤）
                    all_questions = await Question.all()
                    questions = [q for q in all_questions if source_kp.id in (q.knowledge_point_ids or [])]

                    for q in questions:
                        # 将题目从源知识点转移到目标知识点
                        current_ids = q.knowledge_point_ids or []
                        new_ids = [target_kp.id] + [sid for sid in current_ids if sid != source_kp.id and sid != target_kp.id]
                        new_ids = list(dict.fromkeys(new_ids))  # 去重保持顺序
                        q.knowledge_point_ids = new_ids
                        # 更新主知识点
                        if q.knowledge_point_id == source_kp.id:
                            q.knowledge_point_id = target_kp.id
                        await q.save()

                    absorbed_kps.append({"id": source_kp.id, "name": source_kp.name, "merged_into": target_kp.name})
                    source_kp_ids.add(source_kp.id)
                    merged_count += 1
                    kp_logger.debug(f"知识点 {source_kp.name}(id={source_kp.id}) 已合并到 {target_kp.name}(id={target_kp.id})")

            # 删除被合并的源知识点
            if source_kp_ids:
                await KnowledgePoint.filter(id__in=list(source_kp_ids)).delete()
                kp_logger.info(f"已删除被合并的知识点: {list(source_kp_ids)}")

            result = {
                "merged": merged_count,
                "absorbed": absorbed_kps,
                "source_kp_deleted": len(source_kp_ids),
                "message": f"合并完成，共合并{merged_count}个知识点，删除{len(source_kp_ids)}个源知识点"
            }
            kp_logger.info(f"知识点合并完成: {result}")
            return result

        except Exception as e:
            kp_logger.exception(f"知识点合并过程异常: {str(e)}")
            return {"merged": 0, "absorbed": [], "new_kps": [], "message": f"合并失败: {str(e)}"}

    @staticmethod
    def _parse_merge_response(response: str) -> List[Dict]:
        """解析AI返回的合并建议"""
        def normalize(item):
            # 兼容旧格式 source_ids/target_id 和新格式 source_names/target_name
            if 'source_ids' in item and 'source_names' not in item:
                item['source_names'] = item.pop('source_ids')
            if 'target_id' in item and 'target_name' not in item:
                item['target_name'] = item.pop('target_id')
            # 确保是字符串名称
            if 'source_names' in item and isinstance(item['source_names'], list):
                item['source_names'] = [str(x) for x in item['source_names']]
            if 'target_name' in item:
                item['target_name'] = str(item['target_name'])
            return item

        try:
            result = json.loads(response.strip())
            return [normalize(item) for item in result]
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 块
        json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response)
        if json_match:
            try:
                result = json.loads(json_match.group(1).strip())
                return [normalize(item) for item in result]
            except json.JSONDecodeError:
                pass

        # 尝试提取JSON数组
        json_match = re.search(r'(\[\s*\{[\s\S]*\}\s*\])', response)
        if json_match:
            try:
                result = json.loads(json_match.group(1).strip())
                return [normalize(item) for item in result]
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
