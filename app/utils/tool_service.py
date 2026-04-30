from __future__ import annotations

"""Tool execution service."""

import time
import json
import httpx
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import ToolDefinition, TenantToolPermission, ToolCallLog
from app.utils.id import generate_id


class ToolExecutor:
    """Tool execution engine for various tool types."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def check_permission(self, tool_id: str) -> bool:
        """Check if tenant has permission to use the tool."""
        result = await self.db.execute(
            select(TenantToolPermission).where(
                TenantToolPermission.tenant_id == self.tenant_id,
                TenantToolPermission.tool_id == tool_id,
                TenantToolPermission.enabled == True,
            )
        )
        return result.scalar_one_or_none() is not None

    async def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a tool by ID with given arguments."""
        print("\n" + "=" * 60)
        print("[TOOL] 开始执行工具")
        print(f"[TOOL] Tool ID: {tool_id}")
        print(f"[TOOL] Arguments: {json.dumps(arguments, ensure_ascii=False)[:200]}")
        print(f"[TOOL] Tenant ID: {self.tenant_id}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Get tool definition
        print("[TOOL] Step 1: 获取工具定义...")
        result = await self.db.execute(
            select(ToolDefinition).where(ToolDefinition.id == tool_id)
        )
        tool = result.scalar_one_or_none()
        
        if not tool:
            print("[TOOL] ❌ 工具不存在")
            return {"success": False, "error": "工具不存在"}
        
        print(f"[TOOL] ✅ 工具: {tool.name} (type: {tool.type}, status: {tool.status})")
        
        if tool.status != "enabled":
            print("[TOOL] ❌ 工具已禁用")
            return {"success": False, "error": "工具已禁用"}
        
        # Check permission
        print("[TOOL] Step 2: 检查租户权限...")
        has_permission = await self.check_permission(tool_id)
        if not has_permission:
            print("[TOOL] ❌ 租户无权使用该工具")
            return {"success": False, "error": "无权使用该工具"}
        print("[TOOL] ✅ 权限验证通过")
        
        # Execute based on tool type
        print(f"[TOOL] Step 3: 执行工具 (type: {tool.type})...")
        try:
            if tool.type == "internal_api":
                print("[TOOL]    调用内部API...")
                result_data = await self._execute_internal_api(tool, arguments)
            elif tool.type == "database_query":
                print("[TOOL]    执行数据库查询...")
                result_data = await self._execute_database_query(tool, arguments)
            elif tool.type == "http_service":
                print("[TOOL]    调用HTTP服务...")
                result_data = await self._execute_http_service(tool, arguments)
            elif tool.type == "web_scraper":
                print("[TOOL]    执行网页爬取...")
                result_data = await self._execute_web_scraper(tool, arguments)
            elif tool.type == "mcp_tool":
                print("[TOOL]    调用MCP工具...")
                result_data = await self._execute_mcp_tool(tool, arguments)
            else:
                print(f"[TOOL] ❌ 未知工具类型: {tool.type}")
                result_data = {"success": False, "error": f"未知工具类型: {tool.type}"}
            
            status = "success" if result_data.get("success", True) else "failed"
            error_message = None if result_data.get("success", True) else result_data.get("error")
            
            if status == "success":
                print("[TOOL] ✅ 工具执行成功")
            else:
                print(f"[TOOL] ❌ 工具执行失败: {error_message}")
            
        except Exception as e:
            status = "failed"
            error_message = str(e)
            result_data = {"success": False, "error": str(e)}
            print(f"[TOOL] ❌ 执行异常: {str(e)}")
        
        # Log the call
        latency_ms = int((time.time() - start_time) * 1000)
        print(f"[TOOL] Step 4: 记录调用日志 (耗时: {latency_ms}ms)")
        await self._log_call(
            tool=tool,
            request=arguments,
            response=result_data,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            session_id=session_id,
            message_id=message_id,
        )
        
        print("=" * 60)
        print("[TOOL] ✅ 工具执行完成")
        print("=" * 60 + "\n")
        
        return result_data

    async def execute_by_code(
        self,
        tool_code: str,
        arguments: dict[str, Any],
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a tool by code with given arguments."""
        result = await self.db.execute(
            select(ToolDefinition).where(ToolDefinition.code == tool_code)
        )
        tool = result.scalar_one_or_none()
        
        if not tool:
            return {"success": False, "error": "工具不存在"}
        
        return await self.execute(tool.id, arguments, session_id, message_id)

    async def _execute_internal_api(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute internal API tool."""
        config = tool.config or {}
        api_path = config.get("api_path")
        method = config.get("method", "GET").upper()
        
        if not api_path:
            return {"success": False, "error": "工具配置缺少api_path"}
        
        # Internal API calls would go through the app's internal router
        # For now, return a mock response
        return {
            "success": True,
            "data": {
                "message": f"Internal API {method} {api_path} called",
                "arguments": arguments,
            }
        }

    async def _execute_web_scraper(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute web scraper tool - fetch and extract content from web pages."""
        import re
        from urllib.parse import urljoin, urlparse
        
        url = arguments.get("url")
        selector = arguments.get("selector", "body")  # CSS selector or "body" for all
        extract_text = arguments.get("extract_text", True)
        
        if not url:
            return {"success": False, "error": "缺少url参数"}
        
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {"success": False, "error": "无效的URL格式"}
        except Exception:
            return {"success": False, "error": "无效的URL"}
        
        print(f"[TOOL]    爬取URL: {url}")
        print(f"[TOOL]    选择器: {selector}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP请求失败: {response.status_code}",
                        "status_code": response.status_code,
                    }
                
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return {
                        "success": False,
                        "error": f"不支持的内容类型: {content_type}",
                    }
                
                html = response.text
                print(f"[TOOL]    获取到HTML长度: {len(html)}")
                
                # Simple HTML parsing without BeautifulSoup
                # Extract title
                title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip() if title_match else ""
                
                # Remove script and style tags
                clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
                clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.IGNORECASE | re.DOTALL)
                clean_html = re.sub(r'<!--.*?-->', '', clean_html, flags=re.DOTALL)
                
                # Extract text content
                if extract_text:
                    # Remove HTML tags
                    text = re.sub(r'<[^>]+>', ' ', clean_html)
                    # Clean up whitespace
                    text = re.sub(r'\s+', ' ', text)
                    text = text.strip()
                    # Limit length
                    max_length = 5000
                    if len(text) > max_length:
                        text = text[:max_length] + "..."
                else:
                    text = clean_html
                
                # Extract links
                links = []
                link_pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
                for match in re.finditer(link_pattern, html, re.IGNORECASE | re.DOTALL):
                    href = match.group(1)
                    link_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                    if href and not href.startswith('#') and not href.startswith('javascript:'):
                        full_url = urljoin(url, href)
                        links.append({
                            "url": full_url,
                            "text": link_text[:100] if link_text else full_url[:100],
                        })
                
                # Extract meta description
                desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                description = desc_match.group(1) if desc_match else ""
                
                result = {
                    "success": True,
                    "data": {
                        "url": str(response.url),  # Final URL after redirects
                        "title": title,
                        "description": description,
                        "content": text,
                        "links": links[:20],  # Limit to 20 links
                        "status_code": response.status_code,
                    }
                }
                
                print(f"[TOOL]    提取标题: {title}")
                print(f"[TOOL]    内容长度: {len(text)}")
                print(f"[TOOL]    链接数: {len(links)}")
                
                return result
                
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except httpx.RequestError as e:
            return {"success": False, "error": f"请求失败: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"解析失败: {str(e)}"}

    async def _execute_database_query(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute database query tool."""
        config = tool.config or {}
        query_template = config.get("query_template")
        
        if not query_template:
            return {"success": False, "error": "工具配置缺少query_template"}
        
        try:
            # Safely format query with arguments
            # Note: In production, use parameterized queries to prevent SQL injection
            query = query_template.format(**arguments)
            
            result = await self.db.execute(text(query))
            
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys()) if hasattr(result, 'keys') else []
                data = [dict(zip(columns, row)) for row in rows]
                return {"success": True, "data": data, "count": len(data)}
            else:
                return {"success": True, "message": "查询执行成功", "rowcount": result.rowcount}
                
        except Exception as e:
            return {"success": False, "error": f"数据库查询失败: {str(e)}"}

    async def _execute_http_service(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute HTTP service tool - 通用第三方 HTTP 调用.
        
        配置示例（物流轨迹查询）:
        {
            "url": "https://logist.tmexp.com/api/link/orderLocusInfo/getLocusInfoList",
            "method": "POST",
            "timeout": 30,
            "auth": {
                "type": "signature",
                "algorithm": "md5",
                "template": "{app_id}{timestamp}{uuid}{app_secret}",
                "credentials": {
                    "app_id": "TMGJWL",
                    "app_secret": "xxx",
                    "uuid": "xxx"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "timestamp": "{{timestamp}}",
                "uuid": "{{uuid}}",
                "signature": "{{signature}}",
                "linktype": "3"
            },
            "body_template": {
                "innerOrderNo": "{{innerOrderNo}}"
            },
            "param_mapping": {
                "innerOrderNo": {
                    "source": ["innerOrderNo", "order_number", "orderNo"],
                    "type": "array",
                    "required": true,
                    "description": "运单号数组"
                }
            }
        }
        
        简单配置示例（普通HTTP调用）:
        {
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": {
                "Authorization": "Bearer {{api_key}}"
            },
            "credentials": {
                "api_key": "xxx"
            }
        }
        """
        import hashlib
        import re
        
        config = tool.config or {}
        url = config.get("url")
        method = config.get("method", "POST").upper()
        timeout = config.get("timeout", 30)
        
        if not url:
            return {"success": False, "error": "工具配置缺少url"}
        
        print(f"[TOOL]    ┌────────────────────────────────────────────────────────────")
        print(f"[TOOL]    │ [HTTP请求准备]")
        print(f"[TOOL]    │ URL: {url}")
        print(f"[TOOL]    │ Method: {method}")
        print(f"[TOOL]    │ Timeout: {timeout}s")
        print(f"[TOOL]    └────────────────────────────────────────────────────────────")
        print(f"[TOOL]    原始参数: {json.dumps(arguments, ensure_ascii=False)}")
        print(f"[TOOL]    原始参数键名: {list(arguments.keys())}")
        
        # 1. 处理参数映射
        param_mapping = config.get("param_mapping", {})
        print(f"[TOOL]    参数映射配置: {json.dumps(param_mapping, ensure_ascii=False)}")
        processed_args = self._process_param_mapping(arguments, param_mapping)
        if processed_args.get("_error"):
            return {"success": False, "error": processed_args["_error"]}
        print(f"[TOOL]    处理后参数: {json.dumps(processed_args, ensure_ascii=False)}")
        
        # 2. 构建认证变量（签名等）
        auth_config = config.get("auth", {})
        credentials = config.get("credentials", {})
        auth_vars = self._build_auth_vars(auth_config, credentials)
        print(f"[TOOL]    认证变量: {json.dumps({k: '***' if 'secret' in k.lower() or 'key' in k.lower() else v for k, v in auth_vars.items()}, ensure_ascii=False)}")
        
        # 3. 合并所有变量
        all_vars = {**processed_args, **auth_vars}
        
        # 4. 构建请求头（替换模板变量）
        headers = self._render_template(config.get("headers", {}), all_vars)
        print(f"[TOOL]    ┌────────────────────────────────────────────────────────────")
        print(f"[TOOL]    │ [请求头 Headers]")
        for k, v in headers.items():
            # 隐藏敏感信息
            display_v = '***' if 'secret' in k.lower() or 'key' in k.lower() or 'token' in k.lower() else v
            print(f"[TOOL]    │   {k}: {display_v}")
        print(f"[TOOL]    └────────────────────────────────────────────────────────────")
        
        # 5. 构建请求体
        body_template = config.get("body_template")
        if body_template:
            request_body = self._render_template(body_template, all_vars)
        else:
            request_body = processed_args
        print(f"[TOOL]    ┌────────────────────────────────────────────────────────────")
        print(f"[TOOL]    │ [请求体 Request Body]")
        print(f"[TOOL]    │ {json.dumps(request_body, ensure_ascii=False)[:1000]}")
        print(f"[TOOL]    └────────────────────────────────────────────────────────────")
        
        # 6. 替换 URL 中的模板变量
        final_url = self._render_url(url, all_vars)
        print(f"[TOOL]    最终URL: {final_url}")
        
        # 7. 发送请求
        print(f"[TOOL]    ┌────────────────────────────────────────────────────────────")
        print(f"[TOOL]    │ [发送HTTP请求...]")
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(final_url, headers=headers, params=processed_args)
                elif method == "POST":
                    response = await client.post(final_url, json=request_body, headers=headers)
                elif method == "PUT":
                    response = await client.put(final_url, json=request_body, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(final_url, headers=headers)
                else:
                    return {"success": False, "error": f"不支持的HTTP方法: {method}"}
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                print(f"[TOOL]    │ 请求耗时: {elapsed_ms}ms")
                print(f"[TOOL]    │ 响应状态: {response.status_code}")
                
                if 200 <= response.status_code < 300:
                    try:
                        data = response.json()
                        print(f"[TOOL]    │ 响应数据: {json.dumps(data, ensure_ascii=False)[:2000]}")
                    except Exception:
                        data = response.text
                        print(f"[TOOL]    │ 响应文本: {data[:2000]}")
                    print(f"[TOOL]    └────────────────────────────────────────────────────────────")
                    
                    # 处理响应模板
                    result_data = self._process_response_template(config, data)
                    
                    return {"success": True, "data": result_data, "status_code": response.status_code, "elapsed_ms": elapsed_ms}
                else:
                    print(f"[TOOL]    │ 响应错误: {response.text[:1000]}")
                    print(f"[TOOL]    └────────────────────────────────────────────────────────────")
                    return {
                        "success": False, 
                        "error": f"HTTP请求失败: {response.status_code}",
                        "status_code": response.status_code,
                        "body": response.text[:1000] if response.text else None
                    }
        except httpx.TimeoutException:
            print(f"[TOOL]    └────────────────────────────────────────────────────────────")
            return {"success": False, "error": f"请求超时 ({timeout}s)"}
        except httpx.RequestError as e:
            print(f"[TOOL]    └────────────────────────────────────────────────────────────")
            return {"success": False, "error": f"请求失败: {str(e)}"}
    
    def _process_param_mapping(
        self, 
        arguments: dict[str, Any], 
        param_mapping: dict[str, Any]
    ) -> dict[str, Any]:
        """处理参数映射和类型转换。"""
        import re
        
        if not param_mapping:
            # 没有映射配置，直接返回原始参数
            return arguments.copy()
        
        processed = {}
        
        for target_name, mapping in param_mapping.items():
            if isinstance(mapping, dict):
                source_names = mapping.get("source", target_name)
                param_type = mapping.get("type", "string")
                required = mapping.get("required", False)
                default = mapping.get("default")
                extract_pattern = mapping.get("extract_pattern")
                
                # 获取值
                value = None
                
                # 支持多个源名称（优先级从高到低）
                if isinstance(source_names, list):
                    for src in source_names:
                        if src in arguments:
                            value = arguments[src]
                            break
                    # 如果 source 列表中没找到，尝试模糊匹配
                    if value is None and arguments:
                        for src in source_names:
                            src_lower = src.lower().replace("_", "").replace("-", "")
                            for arg_key, arg_value in arguments.items():
                                arg_lower = arg_key.lower().replace("_", "").replace("-", "")
                                if src_lower == arg_lower or src_lower in arg_lower or arg_lower in src_lower:
                                    value = arg_value
                                    print(f"[TOOL]    模糊匹配: {arg_key} -> {src}")
                                    break
                            if value is not None:
                                break
                else:
                    value = arguments.get(source_names)
                
                # 如果还是没找到，且有必填参数，尝试获取第一个非空值
                if value is None and required and arguments:
                    for arg_key, arg_value in arguments.items():
                        if arg_value and not arg_key.startswith("_"):
                            value = arg_value
                            print(f"[TOOL]    自动获取第一个参数: {arg_key} = {value}")
                            break
                
                # 支持正则提取
                if value is None and extract_pattern and arguments.get("_query"):
                    match = re.search(extract_pattern, arguments["_query"])
                    if match:
                        value = match.group()
                
                # 使用默认值
                if value is None and default is not None:
                    value = default
                
                # 必填检查
                if required and value is None:
                    return {"_error": f"缺少必填参数: {target_name}"}
                
                # 类型转换
                if value is not None:
                    if param_type == "array":
                        if isinstance(value, str):
                            value = [value]
                        elif not isinstance(value, list):
                            value = [str(value)]
                    elif param_type == "string":
                        value = str(value) if not isinstance(value, str) else value
                    elif param_type == "number":
                        try:
                            value = float(value) if not isinstance(value, (int, float)) else value
                        except (ValueError, TypeError):
                            return {"_error": f"参数 {target_name} 必须是数字"}
                
                processed[target_name] = value
            else:
                # 简单映射：直接使用值
                processed[target_name] = arguments.get(mapping)
        
        return processed
    
    def _build_auth_vars(
        self, 
        auth_config: dict[str, Any], 
        credentials: dict[str, Any]
    ) -> dict[str, Any]:
        """
        构建认证变量（包括签名）。
        
        支持的认证类型：
        - none: 无认证
        - static: 静态变量（从 credentials 中获取）
        - signature: 签名认证（支持 md5, sha256 等）
        """
        import hashlib
        
        auth_type = auth_config.get("type", "none")
        result = {}
        
        if auth_type == "none":
            # 无认证，只返回 credentials 中的变量
            return credentials.copy()
        
        elif auth_type == "static":
            # 静态变量
            return credentials.copy()
        
        elif auth_type == "signature":
            # 签名认证
            algorithm = auth_config.get("algorithm", "md5")
            template = auth_config.get("template", "")
            
            # 生成时间戳
            import time
            timestamp = str(int(time.time() * 1000))
            result["timestamp"] = timestamp
            
            # 合并 credentials
            all_creds = {**credentials, "timestamp": timestamp}
            
            # 构建签名字符串
            sign_str = template
            for key, value in all_creds.items():
                sign_str = sign_str.replace("{" + key + "}", str(value))
            
            # 计算签名
            if algorithm == "md5":
                signature = hashlib.md5(sign_str.encode()).hexdigest()
            elif algorithm == "sha256":
                signature = hashlib.sha256(sign_str.encode()).hexdigest()
            elif algorithm == "sha1":
                signature = hashlib.sha1(sign_str.encode()).hexdigest()
            else:
                signature = sign_str  # 不加密，直接返回
            
            result["signature"] = signature
            result.update(credentials)
            
            print(f"[TOOL]    签名字符串: {sign_str}")
            print(f"[TOOL]    签名结果: {signature}")
            
            return result
        
        return result
    
    def _render_template(self, template: Any, variables: dict[str, Any]) -> Any:
        """
        渲染模板，替换 {{variable}} 占位符。
        
        支持递归处理 dict, list, str 类型。
        """
        if isinstance(template, dict):
            return {k: self._render_template(v, variables) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._render_template(item, variables) for item in template]
        elif isinstance(template, str):
            result = template
            for key, value in variables.items():
                if isinstance(value, (str, int, float)):
                    result = result.replace("{{" + key + "}}", str(value))
            return result
        else:
            return template
    
    def _render_url(self, url: str, variables: dict[str, Any]) -> str:
        """渲染 URL，替换 {variable} 和 {{variable}} 占位符。"""
        result = url
        for key, value in variables.items():
            if isinstance(value, (str, int, float)):
                result = result.replace("{" + key + "}", str(value))
                result = result.replace("{{" + key + "}}", str(value))
        return result
    
    def _process_response_template(
        self, 
        config: dict[str, Any], 
        data: Any
    ) -> Any:
        """
        处理响应模板，将 API 返回的数据转换为指定格式。
        
        配置示例:
        {
            "response_format": "text",  // "json" 或 "text"
            "response_template": "运单号：{{waybill_no}}\\n状态：{{status}}\\n...",
            "response_fields": {
                "waybill_no": "data.orderNo",
                "status": "data.status",
                "tracks": "data.trackList"
            },
            "list_template": {
                "field": "tracks",
                "item_template": "{{time}} {{location}} {{description}}\\n"
            }
        }
        """
        response_format = config.get("response_format", "json")
        
        # 如果是 JSON 格式或没有配置模板，直接返回原始数据
        if response_format == "json":
            return data
        
        response_template = config.get("response_template")
        if not response_template:
            return data
        
        # 提取字段值
        response_fields = config.get("response_fields", {})
        field_values = {}
        
        for target_name, source_path in response_fields.items():
            value = self._extract_field_value(data, source_path)
            field_values[target_name] = value
        
        # 渲染模板
        result = response_template
        for key, value in field_values.items():
            if value is not None:
                if isinstance(value, list):
                    # 处理列表字段
                    list_config = config.get("list_template", {})
                    if list_config.get("field") == key:
                        item_template = list_config.get("item_template", "{{.}}\\n")
                        list_str = ""
                        for item in value:
                            if isinstance(item, dict):
                                item_str = item_template
                                for k, v in item.items():
                                    item_str = item_str.replace("{{" + k + "}}", str(v) if v else "")
                            else:
                                item_str = item_template.replace("{{.}}", str(item))
                            list_str += item_str
                        result = result.replace("{{" + key + "}}", list_str.strip())
                    else:
                        # 直接转为字符串
                        result = result.replace("{{" + key + "}}", json.dumps(value, ensure_ascii=False))
                else:
                    result = result.replace("{{" + key + "}}", str(value))
        
        print(f"[TOOL]    响应模板渲染结果:\\n{result[:1000]}")
        
        return {"text": result, "raw": data}
    
    def _extract_field_value(self, data: Any, path: str) -> Any:
        """
        从嵌套数据中提取字段值。
        
        支持路径语法：
        - "data.orderNo" -> data["data"]["orderNo"]
        - "data.items[0].name" -> data["data"]["items"][0]["name"]
        """
        if not path:
            return data
        
        current = data
        parts = path.replace("[", ".").replace("]", "").split(".")
        
        for part in parts:
            if not part:
                continue
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index] if 0 <= index < len(current) else None
                except ValueError:
                    return None
            else:
                return None
        
        return current

    async def _execute_mcp_tool(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute MCP tool via stdio or HTTP."""
        import asyncio
        
        config = tool.config or {}
        server_id = config.get("server_id")
        transport_type = config.get("transport_type", "stdio")
        tool_name = tool.code  # Use tool code as MCP tool name
        
        print(f"[TOOL]    MCP工具: {tool_name}")
        print(f"[TOOL]    Server ID: {server_id}")
        print(f"[TOOL]    Transport: {transport_type}")
        print(f"[TOOL]    Arguments: {arguments}")
        
        if transport_type == "stdio":
            # Execute via stdio
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env")
            timeout = config.get("timeout", 30)
            
            if not command:
                return {"success": False, "error": "MCP工具配置缺少command"}
            
            try:
                result = await self._execute_mcp_stdio(
                    command, args, env, tool_name, arguments, timeout
                )
                return result
            except Exception as e:
                return {"success": False, "error": f"MCP调用失败: {str(e)}"}
        
        else:
            # Execute via HTTP/SSE
            base_url = config.get("base_url")
            auth_type = config.get("auth_type", "none")
            auth_config = config.get("auth_config", {})
            
            if not base_url:
                return {"success": False, "error": "MCP工具配置缺少base_url"}
            
            try:
                result = await self._execute_mcp_http(
                    base_url, auth_type, auth_config, tool_name, arguments
                )
                return result
            except Exception as e:
                return {"success": False, "error": f"MCP HTTP调用失败: {str(e)}"}
    
    async def _execute_mcp_stdio(
        self,
        command: str,
        args: list,
        env: dict | None,
        tool_name: str,
        arguments: dict,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Execute MCP tool via stdio transport."""
        import asyncio
        import json
        
        print(f"[TOOL]    启动stdio进程: {command} {args}")
        
        # Build env with current environment
        import os
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=process_env,
        )
        
        try:
            # 1. Initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "ai-assistant", "version": "1.0"}
                }
            }
            
            process.stdin.write((json.dumps(init_request) + "\n").encode())
            await process.stdin.drain()
            
            # Read initialize response
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout
            )
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                process.terminate()
                await process.wait()
                return {"success": False, "error": response["error"].get("message", "初始化失败")}
            
            # 2. Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
            process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
            await process.stdin.drain()
            
            # 3. Call the tool
            call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                }
            }
            
            print(f"[TOOL]    发送工具调用: {json.dumps(call_request)}")
            process.stdin.write((json.dumps(call_request) + "\n").encode())
            await process.stdin.drain()
            
            # Read tool response
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout
            )
            response = json.loads(response_line.decode().strip())
            
            print(f"[TOOL]    收到响应: {response}")
            
            process.terminate()
            await process.wait()
            
            if "result" in response:
                return {
                    "success": True,
                    "data": response["result"].get("content", response["result"]),
                }
            else:
                return {
                    "success": False,
                    "error": response.get("error", {}).get("message", "工具调用失败"),
                }
                
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()
            return {"success": False, "error": "MCP调用超时"}
        except json.JSONDecodeError as e:
            process.terminate()
            await process.wait()
            return {"success": False, "error": f"解析响应失败: {str(e)}"}
        except Exception as e:
            process.terminate()
            await process.wait()
            return {"success": False, "error": str(e)}
    
    async def _execute_mcp_http(
        self,
        base_url: str,
        auth_type: str,
        auth_config: dict,
        tool_name: str,
        arguments: dict,
    ) -> dict[str, Any]:
        """Execute MCP tool via HTTP transport."""
        headers = {}
        if auth_type == "bearer" and auth_config:
            headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"
        elif auth_type == "api_key" and auth_config:
            headers["X-API-Key"] = auth_config.get("api_key", "")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{base_url}/tools/call",
                    json={"name": tool_name, "arguments": arguments},
                    headers=headers,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "data": data.get("content", data)}
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "body": response.text[:500],
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _log_call(
        self,
        tool: ToolDefinition,
        request: dict[str, Any],
        response: dict[str, Any],
        latency_ms: int,
        status: str,
        error_message: str | None = None,
        session_id: str | None = None,
        message_id: str | None = None,
    ):
        """Log tool call to database."""
        log = ToolCallLog(
            id=generate_id(),
            tenant_id=self.tenant_id,
            session_id=session_id,
            message_id=message_id,
            tool_id=tool.id,
            tool_name=tool.name,
            request=request,
            response=response,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.commit()

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """Get all tools available to the current tenant."""
        print(f"[TOOL] get_available_tools - 查询租户可用工具")
        print(f"[TOOL]    tenant_id: {self.tenant_id}")
        
        # First check all permissions for this tenant
        all_perms = await self.db.execute(
            select(TenantToolPermission).where(
                TenantToolPermission.tenant_id == self.tenant_id
            )
        )
        perms = all_perms.scalars().all()
        print(f"[TOOL]    租户权限记录数: {len(perms)}")
        for p in perms:
            print(f"[TOOL]      - tool_id: {p.tool_id}, enabled: {p.enabled}")
        
        # Then check all tools
        all_tools = await self.db.execute(select(ToolDefinition))
        tools_all = all_tools.scalars().all()
        print(f"[TOOL]    系统工具总数: {len(tools_all)}")
        for t in tools_all:
            print(f"[TOOL]      - id: {t.id}, code: {t.code}, status: {t.status}")
        
        # Now do the join query
        result = await self.db.execute(
            select(ToolDefinition, TenantToolPermission)
            .join(TenantToolPermission, ToolDefinition.id == TenantToolPermission.tool_id)
            .where(
                TenantToolPermission.tenant_id == self.tenant_id,
                TenantToolPermission.enabled == True,
                ToolDefinition.status == "enabled",
            )
        )
        
        tools = []
        rows = result.all()
        print(f"[TOOL]    JOIN查询结果数: {len(rows)}")
        
        for tool, perm in rows:
            # 深度合并配置：工具默认配置 + 租户个性化配置
            merged_config = self._merge_config(tool.config, perm.config)
            tools.append({
                "tool_id": tool.id,
                "code": tool.code,
                "name": tool.name,
                "type": tool.type,
                "description": tool.description,
                "config": merged_config,
            })
        
        return tools
    
    def _merge_config(self, base_config: dict | None, override_config: dict | None) -> dict:
        """
        深度合并配置。
        
        租户配置会覆盖工具默认配置，但不会丢失未覆盖的默认值。
        例如：
        - 工具默认配置: {"url": "xxx", "timeout": 30, "credentials": {"app_id": "default"}}
        - 租户配置: {"credentials": {"app_secret": "xxx"}}
        - 合并结果: {"url": "xxx", "timeout": 30, "credentials": {"app_id": "default", "app_secret": "xxx"}}
        """
        if base_config is None and override_config is None:
            return {}
        if base_config is None:
            return override_config.copy()
        if override_config is None:
            return base_config.copy()
        
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并字典
                result[key] = self._merge_config(result[key], value)
            else:
                # 直接覆盖
                result[key] = value
        
        return result
