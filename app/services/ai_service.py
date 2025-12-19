"""AI 服務 - Claude Code (CLI) 整合"""
import asyncio
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from app.services.cache_service import CacheService

logger = logging.getLogger("jaba.ai")


def sanitize_user_input(text: str, max_length: int = 200) -> Tuple[str, list[str]]:
    """
    過濾使用者輸入，防止 prompt injection

    Args:
        text: 原始使用者輸入
        max_length: 最大長度限制

    Returns:
        (sanitized_text, trigger_reasons)
        - sanitized_text: 過濾後的文字
        - trigger_reasons: 觸發原因列表（空列表表示無可疑內容）
    """
    trigger_reasons: list[str] = []
    sanitized = text

    # 0. 先檢查原始長度（記錄但不在此截斷）
    original_too_long = len(text) > max_length

    # 1. 移除 XML/HTML 標籤
    if re.search(r'<[^>]*>', sanitized):
        trigger_reasons.append("xml_tags")
        sanitized = re.sub(r'<[^>]*>', '', sanitized)

    # 2. 移除 markdown code blocks
    if '```' in sanitized:
        trigger_reasons.append("code_blocks")
        sanitized = re.sub(r'```[\s\S]*?```', '', sanitized)
        sanitized = re.sub(r'```', '', sanitized)

    # 3. 移除連續分隔線
    if re.search(r'[-=]{3,}', sanitized):
        trigger_reasons.append("separator_lines")
        sanitized = re.sub(r'[-=]{3,}', '', sanitized)

    # 4. 長度限制（過濾後仍超過才截斷）
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    # 記錄原始訊息過長
    if original_too_long:
        trigger_reasons.append("length_exceeded")

    # 清理多餘空白
    sanitized = ' '.join(sanitized.split())

    return sanitized, trigger_reasons


def estimate_tokens(text: str) -> int:
    """
    簡易估算 token 數量
    中文約 1-2 token/字，英文約 4 字符/token
    這裡使用 len(text) // 2 作為粗估
    """
    if not text:
        return 0
    return len(text) // 2


class AiService:
    """AI 服務 - 使用 Claude Code (CLI)"""

    def __init__(self):
        self.chat_model = "haiku"  # 對話用較快的模型
        self.menu_model = "opus"   # 菜單辨識用較強的模型
        # Claude Code (CLI) 路徑（處理 NVM 安裝的情況）
        self.claude_path = self._find_claude_path()
        # 工作目錄（使用獨立目錄，避免讀取專案的 CLAUDE.md）
        self.working_dir = "/tmp/jaba-ai-cli"
        os.makedirs(self.working_dir, exist_ok=True)

    def _find_claude_path(self) -> str:
        """尋找 Claude Code (CLI) 路徑"""
        import shutil

        # 先嘗試 PATH 中的 claude
        claude_in_path = shutil.which("claude")
        if claude_in_path:
            return claude_in_path

        # 嘗試常見的 NVM 安裝路徑
        home = os.path.expanduser("~")
        nvm_paths = [
            f"{home}/.nvm/versions/node/v24.11.1/bin/claude",
            f"{home}/.nvm/versions/node/v22.11.0/bin/claude",
            f"{home}/.nvm/versions/node/v20.18.0/bin/claude",
        ]

        for path in nvm_paths:
            if os.path.exists(path):
                logger.info(f"Found claude at: {path}")
                return path

        # 找不到就用預設
        logger.warning("Claude Code (CLI) not found, using 'claude' and hoping for the best")
        return "claude"

    async def chat(
        self,
        message: str,
        system_prompt: str,
        context: Optional[dict] = None,
        history: Optional[list] = None,
    ) -> dict:
        """
        與 AI 對話（使用 Claude Code (CLI)）

        Returns:
            {
                "message": "AI 回應文字",
                "actions": [{"type": "action_type", "data": {...}}],
                "_raw": "AI 原始回應（包含思考過程）",
                "_input_prompt": "完整輸入 prompt",
                "_duration_ms": 執行時間毫秒,
                "_model": "使用的模型",
                "_input_tokens": 輸入 token 估算,
                "_output_tokens": 輸出 token 估算
            }
        """
        start_time = time.time()

        try:
            # 格式化對話歷史
            history_str = self._format_chat_history(history) if history else "(無先前對話)"

            # 組合完整訊息
            context_str = json.dumps(context, ensure_ascii=False, indent=2) if context else "{}"
            current_user = context.get("user_name", "使用者") if context else "使用者"

            full_message = f"""[系統上下文]
{context_str}

[對話歷史]
{history_str}

[當前訊息]
{current_user}: {message}

請以 JSON 格式回應：
{{"message": "你的回應訊息", "actions": [{{"type": "動作類型", "data": {{...}}}}, ...] }}

如果不需要執行動作，actions 可以是空陣列 []。"""

            # 組合完整的 input prompt（供日誌記錄）
            input_prompt = f"""[System Prompt]
{system_prompt}

[User Message]
{full_message}"""

            # 建構 Claude Code (CLI) 命令
            cmd = [
                self.claude_path, "-p",
                "--model", self.chat_model,
                "--system-prompt", system_prompt,
                full_message
            ]

            # 使用 asyncio 非同步執行（設定 cwd 確保 CLI 正確執行）
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=120
            )
            stdout = stdout_bytes.decode('utf-8') if stdout_bytes else ''
            stderr = stderr_bytes.decode('utf-8') if stderr_bytes else ''

            # 計算執行時間
            duration_ms = int((time.time() - start_time) * 1000)

            # 解析回應
            result = self._parse_response(stdout, stderr, proc.returncode)

            # 附加日誌資訊
            result["_input_prompt"] = input_prompt
            result["_duration_ms"] = duration_ms
            result["_model"] = self.chat_model
            result["_input_tokens"] = estimate_tokens(input_prompt)
            result["_output_tokens"] = estimate_tokens(result.get("_raw", ""))

            return result

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("AI chat timeout")
            return {
                "message": "抱歉，回應超時了，請再試一次。",
                "actions": [],
                "_raw": "",
                "_input_prompt": "",
                "_duration_ms": duration_ms,
                "_model": self.chat_model,
                "_input_tokens": 0,
                "_output_tokens": 0,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"AI chat error: {e}")
            return {
                "message": "抱歉，我遇到了一些問題，請稍後再試。",
                "actions": [],
                "_raw": "",
                "_input_prompt": "",
                "_duration_ms": duration_ms,
                "_model": self.chat_model,
                "_input_tokens": 0,
                "_output_tokens": 0,
            }

    def _format_chat_history(self, history: list) -> str:
        """格式化對話歷史"""
        if not history:
            return "(無先前對話)"

        lines = []
        for msg in history:
            if msg["role"] == "user":
                # 使用者訊息：顯示名稱
                name = msg.get("name") or "使用者"
                lines.append(f"{name}: {msg['content']}")
            else:
                # assistant / system
                lines.append(f"助手: {msg['content']}")

        return "\n".join(lines)

    def _extract_last_json_object(self, text: str) -> Optional[str]:
        """
        使用括號平衡法提取文字中包含 message 欄位的 JSON 物件
        支援任意巢狀深度
        """
        # 找所有 { 的位置
        brace_positions = [i for i, c in enumerate(text) if c == '{']
        valid_jsons = []

        for start in brace_positions:
            depth = 0
            in_string = False
            escape_next = False

            for i in range(start, len(text)):
                char = text[i]

                if escape_next:
                    escape_next = False
                    continue

                if char == '\\' and in_string:
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        # 找到完整的 JSON 物件
                        candidate = text[start:i+1]
                        # 驗證是否為有效 JSON 且包含 message 欄位
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, dict) and "message" in parsed:
                                valid_jsons.append(candidate)
                        except json.JSONDecodeError:
                            pass
                        break

        # 返回最後一個有效的 JSON（通常是 AI 的最終回應）
        return valid_jsons[-1] if valid_jsons else None

    def _parse_response(self, stdout: str, stderr: str, return_code: int) -> dict:
        """
        解析 Claude Code (CLI) 回應

        擷取策略（按優先順序）：
        1. 優先擷取最後一段 ```json ``` code block
        2. Fallback：尋找最後一個裸 JSON 物件
        """
        response_text = stdout.strip()
        logger.debug(f"AI raw response: {response_text[:200]}..." if len(response_text) > 200 else f"AI raw response: {response_text}")

        if not response_text:
            if return_code != 0:
                return {
                    "message": f"CLI 執行失敗：{stderr or '未知錯誤'}",
                    "actions": [],
                    "_raw": "",
                }
            return {
                "message": "AI 沒有回應",
                "actions": [],
                "_raw": "",
            }

        try:
            # 策略 1：尋找所有 ```json ``` code blocks，取最後一個
            code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
            code_blocks = re.findall(code_block_pattern, response_text)

            json_content = None

            if code_blocks:
                # 取最後一個 code block
                last_block = code_blocks[-1].strip()
                # 嘗試找出其中的 JSON 物件
                json_match = re.search(r'\{[\s\S]*\}', last_block)
                if json_match:
                    json_content = json_match.group()

            # 策略 2：若無 code block，尋找最後一個裸 JSON 物件
            if not json_content:
                # 使用括號平衡法找出完整的 JSON 物件（支援任意巢狀深度）
                json_content = self._extract_last_json_object(response_text)

            if json_content:
                result = json.loads(json_content)
                # 儲存原始回應供日誌使用
                result["_raw"] = response_text
                logger.debug(f"AI parsed result: message='{result.get('message', '')[:50]}...', actions={result.get('actions', [])}")
                return result
            else:
                # 無法找到 JSON，回傳原始文字（可能是非 JSON 回應）
                return {
                    "message": response_text,
                    "actions": [],
                    "_raw": response_text,
                }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}, raw: {json_content[:100] if json_content else 'N/A'}...")
            return {
                "message": response_text,
                "actions": [],
                "_raw": response_text,
            }

    async def recognize_menu(self, image_bytes: bytes) -> dict:
        """
        辨識菜單圖片（使用 Claude Code (CLI) + Read 工具）

        Args:
            image_bytes: 圖片的 bytes 資料

        Returns:
            {
                "categories": [
                    {
                        "name": "分類名稱",
                        "items": [
                            {
                                "name": "品項名稱",
                                "price": 100,
                                "description": "描述",
                                "variants": [{"name": "M", "price": 50}]
                            }
                        ]
                    }
                ]
            }
        """
        # 建立暫存檔
        temp_dir = Path(tempfile.gettempdir()) / "jaba-ai"
        temp_dir.mkdir(exist_ok=True)
        temp_path = str(temp_dir / f"menu_temp_{int(time.time())}.jpg")

        with open(temp_path, 'wb') as f:
            f.write(image_bytes)

        try:
            # 取得菜單辨識提示詞（從快取/DB，無 fallback）
            prompt = CacheService.get_prompt("menu_recognition")
            if not prompt:
                return {"categories": [], "error": "找不到菜單辨識提示詞，請確認資料庫中有 menu_recognition prompt"}

            # 建構 Claude Code (CLI) 命令（使用 Read 工具讀取圖片）
            full_prompt = f"請先使用 Read 工具讀取圖片 {temp_path}，然後{prompt}"
            cmd = [
                self.claude_path, "-p", full_prompt,
                "--model", self.menu_model,
                "--tools", "Read",
                "--allowedTools", "Read",
                "--dangerously-skip-permissions"
            ]

            # 使用 asyncio 非同步執行（設定 cwd 確保 CLI 正確執行）
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=300  # 圖片辨識可能需要較長時間
            )
            response_text = (stdout_bytes.decode('utf-8') if stdout_bytes else '').strip()
            error_text = (stderr_bytes.decode('utf-8') if stderr_bytes else '').strip()

            # 檢查是否有錯誤
            if proc.returncode != 0:
                error_msg = error_text or response_text or "未知錯誤"
                return {"categories": [], "error": f"Claude Code (CLI) 執行失敗：{error_msg}"}

            if not response_text:
                return {"categories": [], "error": f"AI 沒有回應。stderr: {error_text or '(無)'}"}

            # 嘗試解析 JSON 回應
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    menu_data = json.loads(json_match.group())
                    # 確保有 categories 欄位
                    if "categories" in menu_data:
                        return menu_data
                    elif "menu" in menu_data and "categories" in menu_data["menu"]:
                        return menu_data["menu"]
                    else:
                        return {"categories": [], "error": "AI 回應缺少 categories 欄位"}
                except json.JSONDecodeError as e:
                    return {"categories": [], "error": f"AI 回應格式錯誤：{str(e)}"}
            else:
                preview = response_text[:300] if len(response_text) > 300 else response_text
                return {"categories": [], "error": f"AI 回應不包含預期的 JSON 格式。回應：{preview}"}

        except asyncio.TimeoutError:
            return {"categories": [], "error": "辨識超時，請稍後再試"}
        except Exception as e:
            logger.error(f"Menu recognition error: {e}")
            return {"categories": [], "error": str(e)}
        finally:
            # 清理暫存檔
            if os.path.exists(temp_path):
                os.unlink(temp_path)

