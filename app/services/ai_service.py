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


class AiService:
    """AI 服務 - 使用 Claude Code (CLI)"""

    def __init__(self):
        self.chat_model = "haiku"  # 對話用較快的模型
        self.menu_model = "opus"   # 菜單辨識用較強的模型
        # Claude Code (CLI) 路徑（處理 NVM 安裝的情況）
        self.claude_path = self._find_claude_path()
        # 工作目錄（從環境變數讀取，確保 CLI 在正確路徑執行）
        self.working_dir = os.environ.get("PROJECT_ROOT", "/home/ct/SDD/jaba-ai")

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
                "actions": [{"type": "action_type", "data": {...}}]
            }
        """
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

            # 解析回應
            return self._parse_response(stdout, stderr, proc.returncode)

        except asyncio.TimeoutError:
            logger.error("AI chat timeout")
            return {
                "message": "抱歉，回應超時了，請再試一次。",
                "actions": [],
            }
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return {
                "message": "抱歉，我遇到了一些問題，請稍後再試。",
                "actions": [],
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

    def _parse_response(self, stdout: str, stderr: str, return_code: int) -> dict:
        """解析 Claude Code (CLI) 回應"""
        response_text = stdout.strip()
        logger.debug(f"AI raw response: {response_text[:200]}..." if len(response_text) > 200 else f"AI raw response: {response_text}")

        if not response_text:
            if return_code != 0:
                return {
                    "message": f"CLI 執行失敗：{stderr or '未知錯誤'}",
                    "actions": [],
                }
            return {
                "message": "AI 沒有回應",
                "actions": [],
            }

        try:
            # 移除 markdown code block
            clean_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            clean_text = re.sub(r'\s*```$', '', clean_text).strip()

            # 尋找 JSON 內容
            json_match = re.search(r'\{[\s\S]*\}', clean_text)
            if json_match:
                result = json.loads(json_match.group())
                logger.debug(f"AI parsed result: message='{result.get('message', '')[:50]}...', actions={result.get('actions', [])}")
                return result
            else:
                return {
                    "message": response_text,
                    "actions": [],
                }
        except json.JSONDecodeError:
            return {
                "message": response_text,
                "actions": [],
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

