@echo off
REM Docker 快速启动脚本 (Windows)

echo === Docker 部署启动脚本 (Windows) ===
echo.

REM 检查 Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到 Docker，请先安装 Docker Desktop
    pause
    exit /b 1
)

REM 检查环境变量文件
if not exist .env (
    echo 创建 .env 文件...
    (
    echo FLASK_ENV=production
    echo FLASK_PORT=5002
    echo DATABASE_URL=postgresql://examuser:exam_password_123456@db:5432/examdb
    echo DB_PASSWORD=exam_password_123456
    echo MAX_CONTENT_LENGTH=52428800
    echo UPLOAD_FOLDER=uploads
    echo DEEPSEEK_API_KEY=
    echo OPENAI_API_KEY=
    ) > .env
    echo .env 文件已创建
)

REM 创建必要的目录
echo 创建必要的目录...
if not exist uploads mkdir uploads
if not exist logs mkdir logs
if not exist nginx\ssl mkdir nginx\ssl

REM 构建镜像
echo 构建 Docker 镜像...
docker-compose build

REM 启动服务
echo 启动服务...
docker-compose up -d

REM 等待服务就绪
echo 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo === 服务状态 ===
docker-compose ps

REM 初始化数据库
echo.
echo 初始化数据库...
docker-compose exec -T web flask db upgrade

REM 创建管理员账号
echo.
echo 创建管理员账号...
docker-compose exec -T web python create_admin.py

REM 完成
echo.
echo === 部署完成！===
echo.
echo 访问地址:
echo   - HTTP:  http://localhost:5002
echo   - HTTPS: https://localhost (需要配置 SSL 证书)
echo.
echo 管理命令:
echo   - 查看日志: docker-compose logs -f
echo   - 查看状态: docker-compose ps
echo   - 停止服务: docker-compose down
echo   - 重启服务: docker-compose restart
echo.
pause
