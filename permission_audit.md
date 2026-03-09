# 页面权限审计报告

## 需要添加 @login_required 的页面

### main.py 中的问题路由：

1. **`/exams`** (line 117-120)
   - 状态：无 `@login_required`
   - 风险：虽然只是重定向，但应该限制访问

2. **`/exam-select`** (line 123-126)
   - 状态：无 `@login_required`
   - 风险：**高风险** - 学生可以选择考试页面，未登录用户可以查看所有可用的考试

3. **`/exams/<int:exam_id>`** (line 129-144)
   - 状态：无 `@login_required`
   - 风险：**高风险** - 可以查看考试详情，包括题目内容

4. **`/exams/<int:exam_id>/edit`** (line 147-162)
   - 状态：无 `@login_required`
   - 风险：**极高风险** - 可以编辑考试，应该需要管理员权限

5. **`/exams/<int:exam_id>/start`** (line 165-208)
   - 状态：无 `@login_required`
   - 风险：**高风险** - 可以开始考试，虽然有 current_user 检查但不够安全

6. **`/my-submissions`** (line 287-298)
   - 状态：无 `@login_required`
   - 风险：中风险 - 虽然内部有手动检查，但应该使用装饰器

7. **`/subjects`** (line 406-409)
   - 状态：无 `@login_required`
   - 风险：中风险 - 科目管理页面

8. **`/subjects/<int:subject_id>/levels`** (line 412-421)
   - 状态：无 `@login_required`
   - 风险：中风险 - 科目等级管理页面

9. **`/levels`** (line 424-427)
   - 状态：无 `@login_required`
   - 风险：中风险 - 难度级别管理页面

10. **`/questions`** (line 430-433)
    - 状态：无 `@login_required`
    - 风险：中风险 - 问题管理页面（已重定向）

11. **`/questions/create`** (line 436-439)
    - 状态：无 `@login_required`
    - 风险：中风险 - 创建题目页面（已重定向）

12. **`/questions/<int:question_id>/edit`** (line 442-445)
    - 状态：无 `@login_required`
    - 风险：中风险 - 编辑题目页面（已重定向）

13. **`/submissions`** (line 482-485)
    - 状态：无 `@login_required`
    - 风险：中风险 - 提交记录页面（已重定向）

14. **`/ai-configs`** (line 488-491)
    - 状态：无 `@login_required`
    - 风险：高风险 - AI配置管理页面

15. **`/practice`** (line 494-497)
    - 状态：无 `@login_required`
    - 风险：中风险 - 专项刷题页面

### 公开API（不需要登录，但需要评估）：

16. **`/api/health`** (line 507-514)
    - 状态：无 `@login_required`
    - 风险：低风险 - 健康检查接口，通常需要公开

17. **`/api/info`** (line 517-541)
    - 状态：无 `@login_required`
    - 风险：**高风险** - 暴露系统统计信息，建议需要登录

18. **`/api/subjects`** (line 544-554)
    - 状态：无 `@login_required`
    - 风险：中风险 - 科目列表API，建议需要登录

## 建议修复优先级

### P0 - 极高风险（立即修复）
- `/exams/<int:exam_id>/edit` - 编辑考试页面
- `/api/info` - 系统信息接口

### P1 - 高风险（尽快修复）
- `/exam-select` - 考试选择页面
- `/exams/<int:exam_id>` - 考试详情页面
- `/exams/<int:exam_id>/start` - 开始考试页面
- `/ai-configs` - AI配置管理页面

### P2 - 中风险（建议修复）
- `/my-submissions` - 我的考试记录（有手动检查，但建议用装饰器）
- `/subjects` - 科目管理页面
- `/subjects/<int:subject_id>/levels` - 科目等级管理页面
- `/levels` - 难度级别管理页面
- `/practice` - 专项刷题页面
- `/api/subjects` - 科目列表API

### P3 - 低风险（可选）
- `/exams` - 只是重定向
- `/questions` - 只是重定向
- `/questions/create` - 只是重定向
- `/questions/<int:question_id>/edit` - 只是重定向
- `/submissions` - 只是重定向
- `/api/health` - 健康检查接口，通常需要公开
