@echo off
REM 快速部署脚本 - Windows

echo === 在线答题系统快速部署脚本 (Windows) ===
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 检查 pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 pip
    pause
    exit /b 1
)

REM 设置项目目录
set PROJECT_DIR=C:\exam-system
echo [信息] 项目目录: %PROJECT_DIR%

REM 创建项目目录
if not exist "%PROJECT_DIR%" (
    echo [信息] 创建项目目录...
    mkdir "%PROJECT_DIR%"
)

cd /d "%PROJECT_DIR%"

REM 创建虚拟环境
echo [信息] 创建虚拟环境...
python -m venv venv

REM 激活虚拟环境
call venv\Scripts\activate

REM 升级 pip
echo [信息] 升级 pip...
python -m pip install --upgrade pip

REM 安装依赖
echo [信息] 安装 Python 依赖...
pip install -r requirements.txt
pip install wfastcgi

REM 启用 wfastcgi
echo [信息] 启用 wfastcgi...
wfastcgi-enable

REM 配置环境变量
echo [信息] 配置环境变量...
python -c "import secrets; print(secrets.token_hex(32))" > temp_secret.txt
set /p SECRET_KEY=<temp_secret.txt
del temp_secret.txt

(
echo FLASK_ENV=production
echo FLASK_HOST=0.0.0.0
echo FLASK_PORT=5002
echo SECRET_KEY=%SECRET_KEY%
echo DATABASE_URL=sqlite:///%PROJECT_DIR%\exam_system.db
echo MAX_CONTENT_LENGTH=52428800
echo UPLOAD_FOLDER=uploads
echo DEEPSEEK_API_KEY=
echo OPENAI_API_KEY=
) > .env

REM 创建必要的目录
if not exist uploads mkdir uploads
if not exist logs mkdir logs
if not exist instance mkdir instance

REM 初始化数据库
echo [信息] 初始化数据库...
set FLASK_APP=run.py
flask db upgrade

REM 创建管理员账号
echo [信息] 创建管理员账号...
python create_admin.py

REM 创建服务
echo.
echo === 选择部署方式 ===
echo 1. Windows 服务
echo 2. Docker Desktop
echo 3. 手动运行
echo.
set /p choice="请选择部署方式 (1/2/3): "

if "%choice%"=="1" (
    echo [信息] 配置 Windows 服务...
    echo.
    echo 请手动执行以下步骤:
    echo 1. 下载 NSSM: https://nssm.cc/download
    echo 2. 解压并运行 nssm.exe
    echo 3. 安装服务:
    echo    - Path: %PROJECT_DIR%\venv\Scripts\python.exe
    echo    - Startup directory: %PROJECT_DIR%
    echo    - Arguments: run.py
    echo    - Service name: ExamSystem
    echo.
) else if "%choice%"=="2" (
    echo [信息] 检查 Docker...
    docker --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未检测到 Docker Desktop，请先安装
        pause
        exit /b 1
    )
    echo [信息] 使用 Docker 部署...
    docker-compose up -d
) else (
    echo [信息] 配置完成，可以手动运行:
    echo   cd %PROJECT_DIR%
    echo   venv\Scripts\activate
    echo   python run.py
)

REM 完成
echo.
echo === 部署完成！===
echo.
echo 项目目录: %PROJECT_DIR%
echo 访问地址: http://localhost:5002
echo.
pause
