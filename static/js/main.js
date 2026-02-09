// 主JavaScript文件

document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    initTooltips();
    
    // 初始化表单验证
    initFormValidation();
    
    // 初始化答题交互
    initQuestionInteraction();
    
    // 初始化AJAX CSRF令牌
    initCSRFToken();
});

/**
 * 初始化Bootstrap工具提示
 */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover'
        });
    });
}

/**
 * 初始化表单验证
 */
function initFormValidation() {
    // 查找所有需要验证的表单
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
}

/**
 * 初始化答题交互
 */
function initQuestionInteraction() {
    // 单选题和多选题选项选择
    document.querySelectorAll('.question-option').forEach(function(option) {
        option.addEventListener('click', function() {
            const questionId = this.dataset.questionId;
            const optionId = this.dataset.optionId;
            const questionType = this.dataset.questionType;
            
            if (questionType === 'single_choice') {
                // 单选题：取消同一问题的其他选项
                document.querySelectorAll(`[data-question-id="${questionId}"]`)
                    .forEach(function(otherOption) {
                        otherOption.classList.remove('selected');
                    });
                
                this.classList.add('selected');
                
                // 更新隐藏输入框
                const answerInput = document.getElementById(`answer-${questionId}`);
                if (answerInput) {
                    answerInput.value = optionId;
                }
            } else if (questionType === 'multiple_choice') {
                // 多选题：切换选择状态
                this.classList.toggle('selected');
                
                // 更新隐藏输入框
                const answerInput = document.getElementById(`answer-${questionId}`);
                if (answerInput) {
                    const selectedOptions = Array.from(
                        document.querySelectorAll(`[data-question-id="${questionId}"].selected`)
                    ).map(function(opt) {
                        return opt.dataset.optionId;
                    });
                    
                    answerInput.value = selectedOptions.join(',');
                }
            }
        });
    });
}

/**
 * 初始化CSRF令牌
 */
function initCSRFToken() {
    // 从meta标签获取CSRF令牌
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    
    if (csrfToken) {
        // 为所有AJAX请求添加CSRF令牌
        $.ajaxSetup({
            headers: {
                'X-CSRF-Token': csrfToken
            }
        });
        
        // 或者使用fetch API
        if (window.fetch) {
            const originalFetch = window.fetch;
            window.fetch = function(resource, options) {
                options = options || {};
                options.headers = options.headers || {};
                options.headers['X-CSRF-Token'] = csrfToken;
                return originalFetch(resource, options);
            };
        }
    }
}

/**
 * 显示加载动画
 */
function showLoading(element) {
    if (element) {
        const originalContent = element.innerHTML;
        element.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            加载中...
        `;
        element.disabled = true;
        element.dataset.originalContent = originalContent;
    }
}

/**
 * 隐藏加载动画
 */
function hideLoading(element) {
    if (element && element.dataset.originalContent) {
        element.innerHTML = element.dataset.originalContent;
        element.disabled = false;
        delete element.dataset.originalContent;
    }
}

/**
 * 显示成功消息
 */
function showSuccess(message, containerId = 'alerts-container') {
    showAlert('success', message, containerId);
}

/**
 * 显示错误消息
 */
function showError(message, containerId = 'alerts-container') {
    showAlert('danger', message, containerId);
}

/**
 * 显示警告消息
 */
function showWarning(message, containerId = 'alerts-container') {
    showAlert('warning', message, containerId);
}

/**
 * 显示消息
 */
function showAlert(type, message, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    container.innerHTML = alertHtml + container.innerHTML;
    
    // 5秒后自动消失
    setTimeout(function() {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, 5000);
}

/**
 * 文件上传处理
 */
function handleFileUpload(inputId, previewId, maxSizeMB = 10) {
    const fileInput = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    
    if (!fileInput || !preview) return;
    
    fileInput.addEventListener('change', function(event) {
        const file = event.target.files[0];
        
        if (!file) {
            preview.innerHTML = '<p class="text-muted">未选择文件</p>';
            return;
        }
        
        // 检查文件大小
        const maxSize = maxSizeMB * 1024 * 1024;
        if (file.size > maxSize) {
            showError(`文件大小超过${maxSizeMB}MB限制`);
            fileInput.value = '';
            preview.innerHTML = '<p class="text-muted">未选择文件</p>';
            return;
        }
        
        // 检查文件类型
        const allowedTypes = [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
            'application/msword', // .doc
            'application/pdf',
            'text/plain'
        ];
        
        if (!allowedTypes.includes(file.type)) {
            showError('不支持的文件类型，请上传Word文档、PDF或文本文件');
            fileInput.value = '';
            preview.innerHTML = '<p class="text-muted">未选择文件</p>';
            return;
        }
        
        // 显示文件信息
        preview.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">${file.name}</h6>
                    <p class="card-text small text-muted">
                        大小: ${(file.size / 1024 / 1024).toFixed(2)} MB<br>
                        类型: ${file.type}<br>
                        最后修改: ${new Date(file.lastModified).toLocaleString()}
                    </p>
                </div>
            </div>
        `;
    });
}