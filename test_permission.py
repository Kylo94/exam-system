#!/usr/bin/env python3
"""
测试脚本：检查哪些页面可以无需登录访问
"""

import requests
from urllib.parse import urljoin

# 基础URL
BASE_URL = "http://localhost:5000"

# 需要测试的页面列表（预期需要登录的页面）
NEED_LOGIN_PAGES = [
    '/dashboard',
    '/exams',
    '/exam-select',
    '/exams/1',
    '/exams/1/edit',
    '/exams/1/start',
    '/my-submissions',
    '/subjects',
    '/levels',
    '/questions',
    '/questions/create',
    '/upload',
    '/exam-manage',
    '/submissions',
    '/ai-configs',
    '/practice',
    '/api/questions/1',
    '/api/submissions',
]

# 公开页面（预期不需要登录的页面）
PUBLIC_PAGES = [
    '/',
    '/api/health',
    '/api/info',
    '/api/subjects',
]

def test_page(url, should_need_login=True):
    """测试单个页面"""
    try:
        response = requests.get(url, timeout=5, allow_redirects=False)

        # 检查响应状态码
        if should_need_login:
            # 预期需要登录的页面
            if response.status_code in [302, 401, 403]:
                # 重定向到登录页面或返回未授权错误 - 这是正确的
                return True, f"✓ 正确 - 状态码 {response.status_code} (需要登录)"
            elif response.status_code == 200:
                # 返回200但有可能是重定向后的页面，检查URL
                return False, f"✗ 错误 - 状态码 {response.status_code} (应该需要登录但可以直接访问)"
            else:
                return False, f"? 未知 - 状态码 {response.status_code}"
        else:
            # 预期公开的页面
            if response.status_code == 200:
                return True, f"✓ 正确 - 状态码 {response.status_code} (公开访问)"
            else:
                return False, f"✗ 错误 - 状态码 {response.status_code} (应该是公开页面)"

    except requests.RequestException as e:
        return False, f"✗ 连接错误: {str(e)}"

def main():
    print("=" * 80)
    print("开始测试页面权限控制...")
    print("=" * 80)
    print()

    # 测试预期需要登录的页面
    print("【预期需要登录的页面】")
    print("-" * 80)
    need_login_issues = []
    for page in NEED_LOGIN_PAGES:
        url = urljoin(BASE_URL, page)
        success, message = test_page(url, should_need_login=True)
        print(f"{page:40s} - {message}")
        if not success:
            need_login_issues.append(page)

    print()
    print("=" * 80)
    print()

    # 测试预期公开的页面
    print("【预期公开的页面】")
    print("-" * 80)
    public_issues = []
    for page in PUBLIC_PAGES:
        url = urljoin(BASE_URL, page)
        success, message = test_page(url, should_need_login=False)
        print(f"{page:40s} - {message}")
        if not success:
            public_issues.append(page)

    print()
    print("=" * 80)
    print()

    # 汇总结果
    print("【测试结果汇总】")
    print("-" * 80)
    total_pages = len(NEED_LOGIN_PAGES) + len(PUBLIC_PAGES)
    tested_pages = total_pages
    issue_count = len(need_login_issues) + len(public_issues)

    if need_login_issues:
        print(f"⚠️  以下页面应该需要登录但可以直接访问（安全风险）：")
        for page in need_login_issues:
            print(f"   - {page}")
        print()

    if public_issues:
        print(f"⚠️  以下公开页面无法访问：")
        for page in public_issues:
            print(f"   - {page}")
        print()

    if not need_login_issues and not public_issues:
        print("✅ 所有页面权限控制正常！")
    else:
        print(f"❌ 发现 {issue_count} 个问题，需要修复")

    print()
    print(f"测试完成：共测试 {tested_pages} 个页面")
    print("=" * 80)

if __name__ == '__main__':
    main()
