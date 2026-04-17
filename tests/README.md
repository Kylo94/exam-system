# 单元测试

## 运行测试

```bash
# 安装测试依赖
pip install -r requirements-test.txt

# 运行所有测试
pytest

# 运行特定模块
pytest tests/test_models.py -v
pytest tests/test_auth.py -v
pytest tests/test_validators.py -v

# 带覆盖率报告
pytest --cov=app --cov-report=term-missing
```

## 测试结构

```
tests/
├── conftest.py          # pytest 配置和 fixtures
├── test_models.py       # 模型单元测试
├── test_auth.py          # 认证功能测试
└── test_validators.py     # 数据验证器测试
```

## 测试覆盖

| 模块 | 测试内容 |
|------|---------|
| test_models | User/Subject/Level/Exam/Question 模型 |
| test_auth | 密码哈希、JWT令牌、角色权限 |
| test_validators | 字符串/整数/邮箱/手机号/URL等验证 |
