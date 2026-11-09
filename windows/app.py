# -*- coding: utf-8 -*-
"""
AI Agent Hub - Windows Desktop Client
Native multi-agent AI chat application with support for OpenAI-compatible APIs & Google Gemini,
image/vision attachments, persistent local conversation storage, and modern dark UI with Persian RTL support.
"""

import sys
import os
import json
import uuid
import io
import base64
from dataclasses import dataclass, asdict, field
from typing import List, Optional

import requests
from PIL import Image

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QScrollArea, QFrame,
    QDialog, QRadioButton, QButtonGroup, QMessageBox, QFileDialog,
    QProgressBar, QSplitter, QSizePolicy, QToolButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap, QImage, QColor, QPalette


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
AGENTS_FILE = os.path.join(DATA_DIR, "agents_data.json")


@dataclass
class AiAgent:
    name: str
    provider: str  # "OPENAI_COMPATIBLE" or "GEMINI"
    base_url: str
    api_key: str
    model_name: str
    system_prompt: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    image_base64: Optional[str] = None


def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def load_agents() -> List[AiAgent]:
    ensure_data_dir()
    if not os.path.exists(AGENTS_FILE):
        return []
    try:
        with open(AGENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [AiAgent(**item) for item in data]
    except Exception as e:
        print(f"Error loading agents: {e}")
        return []


def save_agents(agents: List[AiAgent]):
    ensure_data_dir()
    try:
        with open(AGENTS_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in agents], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving agents: {e}")


def load_chat_history(agent_id: str) -> List[ChatMessage]:
    ensure_data_dir()
    chat_file = os.path.join(DATA_DIR, f"chat_{agent_id}.json")
    if not os.path.exists(chat_file):
        return []
    try:
        with open(chat_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [ChatMessage(**item) for item in data]
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []


def save_chat_history(agent_id: str, history: List[ChatMessage]):
    ensure_data_dir()
    chat_file = os.path.join(DATA_DIR, f"chat_{agent_id}.json")
    try:
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in history], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")


def delete_chat_history(agent_id: str):
    ensure_data_dir()
    chat_file = os.path.join(DATA_DIR, f"chat_{agent_id}.json")
    if os.path.exists(chat_file):
        try:
            os.remove(chat_file)
        except Exception:
            pass


def process_image_to_base64(file_path: str, max_dimension: int = 1024) -> Optional[str]:
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            ratio = min(max_dimension / max(img.width, img.height), 1.0)
            if ratio < 1.0:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Image processing error: {e}")
        return None


def base64_to_pixmap(b64_str: str) -> Optional[QPixmap]:
    try:
        img_bytes = base64.b64decode(b64_str)
        qimg = QImage()
        if qimg.loadFromData(img_bytes):
            return QPixmap.fromImage(qimg)
    except Exception:
        pass
    return None


class ApiWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, agent: AiAgent, history: List[ChatMessage]):
        super().__init__()
        self.agent = agent
        self.history = history

    def run(self):
        try:
            session = requests.Session()
            if self.agent.provider == "GEMINI":
                clean_base = self.agent.base_url.strip().rstrip('/')
                if "/models" in clean_base or "/v1beta" in clean_base or "/v1" in clean_base:
                    final_base = clean_base
                else:
                    final_base = f"{clean_base}/v1beta/models"

                url = f"{final_base}/{self.agent.model_name.strip()}:generateContent?key={self.agent.api_key.strip()}"

                root_json = {}
                if self.agent.system_prompt.strip():
                    root_json["systemInstruction"] = {
                        "parts": [{"text": self.agent.system_prompt.strip()}]
                    }

                contents = []
                for msg in self.history:
                    role = "user" if msg.role == "user" else "model"
                    parts = [{"text": msg.content}]
                    if msg.image_base64:
                        parts.append({
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": msg.image_base64
                            }
                        })
                    contents.append({"role": role, "parts": parts})

                root_json["contents"] = contents

                response = session.post(url, json=root_json, timeout=90)
                if not response.ok:
                    self.error.emit(f"خطای سرور گوگل ({response.status_code}):\n{response.text}")
                    return

                res_json = response.json()
                if "error" in res_json:
                    self.error.emit(f"خطای جمینای: {res_json['error'].get('message', str(res_json))}")
                    return

                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "بدون پاسخ متنی")
                        self.finished.emit(text)
                        return
                self.finished.emit("جمینای پاسخی برنگرداند (احتمالاً به دلیل فیلتر محتوا).")

            else:  # OPENAI_COMPATIBLE
                clean_base = self.agent.base_url.strip().rstrip('/')
                if clean_base.endswith("/chat/completions"):
                    endpoint = clean_base
                elif clean_base.endswith("/v1"):
                    endpoint = f"{clean_base}/chat/completions"
                else:
                    endpoint = clean_base

                messages = []
                if self.agent.system_prompt.strip():
                    messages.append({"role": "system", "content": self.agent.system_prompt.strip()})

                for msg in self.history:
                    if msg.image_base64 and msg.role == "user":
                        messages.append({
                            "role": "user",
                            "content": [
                                {"type": "text", "text": msg.content},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{msg.image_base64}"}
                                }
                            ]
                        })
                    else:
                        messages.append({"role": msg.role, "content": msg.content})

                body = {
                    "model": self.agent.model_name.strip(),
                    "messages": messages
                }
                headers = {
                    "Authorization": f"Bearer {self.agent.api_key.strip()}",
                    "Content-Type": "application/json"
                }

                response = session.post(endpoint, json=body, headers=headers, timeout=90)
                if not response.ok:
                    self.error.emit(f"خطای سرور ({response.status_code}):\n{response.text}")
                    return

                res_json = response.json()
                if "error" in res_json:
                    self.error.emit(f"خطای مدل: {res_json['error'].get('message', str(res_json))}")
                    return

                choices = res_json.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "بدون پاسخ متنی")
                    self.finished.emit(content)
                else:
                    self.finished.emit("پاسخی از مدل دریافت نشد.")

        except Exception as e:
            self.error.emit(f"خطا در برقراری ارتباط با هوش مصنوعی:\n{str(e)}")


class AgentDialog(QDialog):
    def __init__(self, parent=None, agent: Optional[AiAgent] = None):
        super().__init__(parent)
        self.agent = agent
        self.setWindowTitle("تعریف ایجنت جدید" if agent is None else "ویرایش ایجنت")
        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Name
        layout.addWidget(QLabel("نام ایجنت:"))
        self.name_edit = QLineEdit(self.agent.name if self.agent else "")
        self.name_edit.setPlaceholderText("مثلاً: دستیار برنامه‌نویسی یا کارشناس محتوا")
        layout.addWidget(self.name_edit)

        # Provider Radio
        layout.addWidget(QLabel("نوع ارائه‌دهنده هوش مصنوعی:"))
        radio_layout = QHBoxLayout()
        self.btn_openai = QRadioButton("OpenAI / OpenRouter / DeepSeek / Groq")
        self.btn_gemini = QRadioButton("Google Gemini")

        current_prov = self.agent.provider if self.agent else "OPENAI_COMPATIBLE"
        if current_prov == "GEMINI":
            self.btn_gemini.setChecked(True)
        else:
            self.btn_openai.setChecked(True)

        self.btn_openai.toggled.connect(self.on_provider_changed)
        radio_layout.addWidget(self.btn_openai)
        radio_layout.addWidget(self.btn_gemini)
        layout.addLayout(radio_layout)

        # Base URL
        layout.addWidget(QLabel("آدرس سرور / Endpoint (Base URL):"))
        default_base = (
            self.agent.base_url if self.agent else "https://api.openai.com/v1/chat/completions"
        )
        self.url_edit = QLineEdit(default_base)
        layout.addWidget(self.url_edit)

        # Model ID
        layout.addWidget(QLabel("نام مدل (Model ID):"))
        default_model = self.agent.model_name if self.agent else "gpt-4o-mini"
        self.model_edit = QLineEdit(default_model)
        layout.addWidget(self.model_edit)

        # API Key
        layout.addWidget(QLabel("کلید API (API Key):"))
        self.key_edit = QLineEdit(self.agent.api_key if self.agent else "")
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("sk-...")
        layout.addWidget(self.key_edit)

        # System Prompt
        layout.addWidget(QLabel("دستورالعمل سیستم (System Prompt):"))
        self.prompt_edit = QTextEdit(
            self.agent.system_prompt if self.agent else "تو یک دستیار هوشمند، دقیق و مؤدب هستی."
        )
        self.prompt_edit.setFixedHeight(90)
        layout.addWidget(self.prompt_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("ذخیره ایجنت")
        self.save_btn.setStyleSheet("background-color: #7C4DFF; color: white; font-weight: bold; padding: 6px 18px;")
        self.save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def on_provider_changed(self):
        if self.btn_gemini.isChecked():
            if not self.agent or self.agent.provider != "GEMINI":
                self.url_edit.setText("https://generativelanguage.googleapis.com/v1beta/models")
                self.model_edit.setText("gemini-2.5-flash")
        else:
            if not self.agent or self.agent.provider == "GEMINI":
                self.url_edit.setText("https://api.openai.com/v1/chat/completions")
                self.model_edit.setText("gpt-4o-mini")

    def save_and_close(self):
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        model = self.model_edit.text().strip()
        key = self.key_edit.text().strip()
        prompt = self.prompt_edit.toPlainText().strip()
        provider = "GEMINI" if self.btn_gemini.isChecked() else "OPENAI_COMPATIBLE"

        if not name or not url or not model or not key:
            QMessageBox.warning(self, "فیلدهای ناقص", "لطفاً تمامی موارد نام، آدرس سرور، مدل و کلید API را وارد کنید.")
            return

        self.agent_data = AiAgent(
            id=self.agent.id if self.agent else str(uuid.uuid4()),
            name=name,
            provider=provider,
            base_url=url,
            apiKey=key if hasattr(self.agent, "apiKey") else key,
            api_key=key,
            model_name=model,
            system_prompt=prompt
        )
        self.accept()


class MessageBubble(QFrame):
    def __init__(self, message: ChatMessage, on_copy_callback):
        super().__init__()
        self.message = message
        self.on_copy_callback = on_copy_callback
        self.init_ui()

    def init_ui(self):
        is_user = self.message.role == "user"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Style frame
        if is_user:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2E3856;
                    border-radius: 12px;
                    border: 1px solid #3E4B72;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1F2430;
                    border-radius: 12px;
                    border: 1px solid #2B3345;
                }
            """)

        # Header with role & copy
        header_layout = QHBoxLayout()
        role_label = QLabel("شما" if is_user else "پاسخ ایجنت")
        role_label.setFont(QFont("Tahoma", 9, QFont.Bold))
        role_label.setStyleSheet("color: #9EBBFF;" if is_user else "color: #98C379;")
        header_layout.addWidget(role_label)
        header_layout.addStretch()

        copy_btn = QToolButton()
        copy_btn.setText("📋 کپی")
        copy_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: #A0A0A0;
                border: none;
                font-size: 11px;
            }
            QToolButton:hover {
                color: #FFFFFF;
            }
        """)
        copy_btn.clicked.connect(lambda: self.on_copy_callback(self.message.content))
        header_layout.addWidget(copy_btn)
        layout.addLayout(header_layout)

        # Image if attached
        if self.message.image_base64:
            pixmap = base64_to_pixmap(self.message.image_base64)
            if pixmap:
                img_label = QLabel()
                scaled = pixmap.scaledToWidth(300, Qt.SmoothTransformation)
                img_label.setPixmap(scaled)
                img_label.setStyleSheet("border-radius: 8px; border: 1px solid #444;")
                layout.addWidget(img_label)

        # Message Text
        content_label = QLabel(self.message.content)
        content_label.setFont(QFont("Tahoma", 10))
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_label.setStyleSheet("color: #E6E6E6; line-height: 140%;")
        layout.addWidget(content_label)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Agent Hub - نگارش ویندوز")
        self.resize(1000, 700)
        self.agents: List[AiAgent] = load_agents()
        self.selected_agent: Optional[AiAgent] = self.agents[0] if self.agents else None
        self.current_messages: List[ChatMessage] = []
        self.attached_image_b64: Optional[str] = None
        self.api_thread: Optional[ApiWorker] = None

        self.apply_dark_theme()
        self.init_ui()

        if self.selected_agent:
            self.load_active_agent_chat()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #12151C;
                color: #EAEAEA;
                font-family: 'Segoe UI', 'Tahoma', sans-serif;
            }
            QLineEdit, QTextEdit {
                background-color: #1A1E29;
                border: 1px solid #2F374A;
                border-radius: 8px;
                padding: 8px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #7C4DFF;
            }
            QPushButton {
                background-color: #283042;
                border: 1px solid #364159;
                border-radius: 8px;
                padding: 8px 14px;
                color: #FFFFFF;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #353F57;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #141720;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #2D374D;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #48587B;
            }
        """)

    def init_ui(self):
        main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(main_splitter)

        # ----------------- SIDEBAR (AGENTS) -----------------
        sidebar_widget = QWidget()
        sidebar_widget.setMinimumWidth(260)
        sidebar_widget.setMaximumWidth(340)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(12)

        side_header = QHBoxLayout()
        side_title = QLabel("لیست ایجنت‌ها")
        side_title.setFont(QFont("Tahoma", 12, QFont.Bold))
        side_header.addWidget(side_title)
        side_header.addStretch()

        add_agent_btn = QPushButton("+ جدید")
        add_agent_btn.setStyleSheet("background-color: #7C4DFF; font-weight: bold;")
        add_agent_btn.clicked.connect(self.open_add_agent_dialog)
        side_header.addWidget(add_agent_btn)
        sidebar_layout.addLayout(side_header)

        # Agent List Container
        self.agent_scroll = QScrollArea()
        self.agent_scroll.setWidgetResizable(True)
        self.agent_list_container = QWidget()
        self.agent_list_layout = QVBoxLayout(self.agent_list_container)
        self.agent_list_layout.setSpacing(8)
        self.agent_list_layout.addStretch()
        self.agent_scroll.setWidget(self.agent_list_container)
        sidebar_layout.addWidget(self.agent_scroll)

        main_splitter.addWidget(sidebar_widget)

        # ----------------- MAIN CHAT AREA -----------------
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(16, 16, 16, 16)
        chat_layout.setSpacing(10)

        # Top Bar
        top_bar = QHBoxLayout()
        self.agent_info_title = QLabel("ایجنتی انتخاب نشده")
        self.agent_info_title.setFont(QFont("Tahoma", 13, QFont.Bold))
        top_bar.addWidget(self.agent_info_title)

        self.agent_info_subtitle = QLabel("")
        self.agent_info_subtitle.setStyleSheet("color: #8C98B2; font-size: 11px;")
        top_bar.addWidget(self.agent_info_subtitle)
        top_bar.addStretch()

        self.clear_chat_btn = QPushButton("پاکسازی چت")
        self.clear_chat_btn.setStyleSheet("background-color: #3B202A; color: #FF8595; border: 1px solid #5A2A38;")
        self.clear_chat_btn.clicked.connect(self.clear_current_chat)
        top_bar.addWidget(self.clear_chat_btn)
        chat_layout.addLayout(top_bar)

        # Chat Message Scroll Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setSpacing(12)
        self.messages_layout.addStretch()
        self.chat_scroll.setWidget(self.messages_container)
        chat_layout.addWidget(self.chat_scroll)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: transparent;
            }
            QProgressBar::chunk {
                background-color: #7C4DFF;
            }
        """)
        self.progress_bar.setVisible(False)
        chat_layout.addWidget(self.progress_bar)

        # Image preview bar
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet("background-color: #1A1F2C; border-radius: 8px; padding: 4px;")
        self.preview_frame.setVisible(False)
        preview_layout = QHBoxLayout(self.preview_frame)
        self.preview_img_label = QLabel()
        self.preview_img_label.setFixedSize(48, 48)
        self.preview_img_label.setScaledContents(True)
        preview_layout.addWidget(self.preview_img_label)
        self.preview_text = QLabel("تصویر ضمیمه شد و آماده ارسال است")
        self.preview_text.setStyleSheet("color: #AAB; font-size: 12px;")
        preview_layout.addWidget(self.preview_text)
        preview_layout.addStretch()
        remove_img_btn = QPushButton("✕")
        remove_img_btn.setFixedSize(28, 28)
        remove_img_btn.clicked.connect(self.remove_attached_image)
        preview_layout.addWidget(remove_img_btn)
        chat_layout.addWidget(self.preview_frame)

        # Bottom Input Area
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        self.attach_btn = QPushButton("📎 تصویر")
        self.attach_btn.setToolTip("انتخاب تصویر از سیستم جهت بررسی چندوجهی (Vision)")
        self.attach_btn.clicked.connect(self.select_image_attachment)
        input_bar.addWidget(self.attach_btn)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("پیام خود را بنویسید... (Ctrl+Enter یا زدن دکمه ارسال)")
        self.input_edit.setFixedHeight(50)
        input_bar.addWidget(self.input_edit)

        self.send_btn = QPushButton("ارسال ➤")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #7C4DFF;
                color: #FFFFFF;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #9269FF;
            }
            QPushButton:disabled {
                background-color: #3E3E52;
                color: #777;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_bar.addWidget(self.send_btn)

        chat_layout.addLayout(input_bar)
        main_splitter.addWidget(chat_widget)
        main_splitter.setStretchFactor(1, 4)

        self.refresh_agents_list()

    def refresh_agents_list(self):
        # Clear existing agent cards
        while self.agent_list_layout.count() > 1:
            item = self.agent_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for agent in self.agents:
            card = QFrame()
            is_active = self.selected_agent and self.selected_agent.id == agent.id
            if is_active:
                card.setStyleSheet("""
                    QFrame {
                        background-color: #2A3347;
                        border-radius: 8px;
                        border: 1px solid #7C4DFF;
                    }
                """)
            else:
                card.setStyleSheet("""
                    QFrame {
                        background-color: #171B24;
                        border-radius: 8px;
                        border: 1px solid #232B3A;
                    }
                    QFrame:hover {
                        background-color: #1F2533;
                    }
                """)

            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)

            info_layout = QVBoxLayout()
            name_lbl = QLabel(agent.name)
            name_lbl.setFont(QFont("Tahoma", 10, QFont.Bold))
            info_layout.addWidget(name_lbl)

            model_lbl = QLabel(agent.model_name)
            model_lbl.setStyleSheet("color: #7886A0; font-size: 11px;")
            info_layout.addWidget(model_lbl)
            card_layout.addLayout(info_layout)
            card_layout.addStretch()

            # Action buttons
            edit_btn = QToolButton()
            edit_btn.setText("✏️")
            edit_btn.setToolTip("ویرایش")
            edit_btn.setStyleSheet("background: transparent; border: none;")
            edit_btn.clicked.connect(lambda _, a=agent: self.open_edit_agent_dialog(a))
            card_layout.addWidget(edit_btn)

            del_btn = QToolButton()
            del_btn.setText("🗑️")
            del_btn.setToolTip("حذف")
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.clicked.connect(lambda _, a=agent: self.delete_agent(a))
            card_layout.addWidget(del_btn)

            # Make the card selectable
            card.mousePressEvent = lambda e, a=agent: self.select_agent(a)
            self.agent_list_layout.insertWidget(self.agent_list_layout.count() - 1, card)

        if not self.agents:
            empty_lbl = QLabel("هیچ ایجنتی وجود ندارد.\nروی دکمه '+ جدید' کلیک کنید.")
            empty_lbl.setStyleSheet("color: #6C7A92; padding: 20px; text-align: center;")
            self.agent_list_layout.insertWidget(0, empty_lbl)

    def select_agent(self, agent: AiAgent):
        self.selected_agent = agent
        self.refresh_agents_list()
        self.load_active_agent_chat()

    def load_active_agent_chat(self):
        if not self.selected_agent:
            self.agent_info_title.setText("ایجنتی انتخاب نشده")
            self.agent_info_subtitle.setText("")
            self.clear_chat_display()
            return

        self.agent_info_title.setText(self.selected_agent.name)
        self.agent_info_subtitle.setText(f"{self.selected_agent.provider} | {self.selected_agent.model_name}")

        self.current_messages = load_chat_history(self.selected_agent.id)
        self.render_chat_messages()

    def clear_chat_display(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def render_chat_messages(self):
        self.clear_chat_display()
        for msg in self.current_messages:
            bubble = MessageBubble(msg, self.copy_to_clipboard)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)

        QTimer.singleShot(50, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def copy_to_clipboard(self, text: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "کپی شد", "متن پیام در کلیپ‌بورد کپی شد.")

    def open_add_agent_dialog(self):
        dialog = AgentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_agent = dialog.agent_data
            self.agents.append(new_agent)
            save_agents(self.agents)
            self.selected_agent = new_agent
            self.refresh_agents_list()
            self.load_active_agent_chat()

    def open_edit_agent_dialog(self, agent: AiAgent):
        dialog = AgentDialog(self, agent)
        if dialog.exec_() == QDialog.Accepted:
            updated = dialog.agent_data
            for idx, a in enumerate(self.agents):
                if a.id == updated.id:
                    self.agents[idx] = updated
                    break
            save_agents(self.agents)
            if self.selected_agent and self.selected_agent.id == updated.id:
                self.selected_agent = updated
            self.refresh_agents_list()
            self.load_active_agent_chat()

    def delete_agent(self, agent: AiAgent):
        confirm = QMessageBox.question(
            self, "حذف ایجنت",
            f"آیا از حذف ایجنت '{agent.name}' و تاریخچه گفتگوهای آن مطمئن هستید؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            delete_chat_history(agent.id)
            self.agents = [a for a in self.agents if a.id != agent.id]
            save_agents(self.agents)
            if self.selected_agent and self.selected_agent.id == agent.id:
                self.selected_agent = self.agents[0] if self.agents else None
            self.refresh_agents_list()
            self.load_active_agent_chat()

    def clear_current_chat(self):
        if not self.selected_agent:
            return
        confirm = QMessageBox.question(
            self, "پاکسازی چت",
            "آیا مطمئن هستید که می‌خواهید تمام تاریخچه این گفتگو را پاک کنید؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            delete_chat_history(self.selected_agent.id)
            self.current_messages = []
            self.render_chat_messages()

    def select_image_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب تصویر", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if file_path:
            b64 = process_image_to_base64(file_path)
            if b64:
                self.attached_image_b64 = b64
                pixmap = base64_to_pixmap(b64)
                if pixmap:
                    self.preview_img_label.setPixmap(pixmap)
                self.preview_frame.setVisible(True)

    def remove_attached_image(self):
        self.attached_image_b64 = None
        self.preview_frame.setVisible(False)

    def send_message(self):
        if not self.selected_agent:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا یک ایجنت بسازید یا انتخاب کنید.")
            return

        text = self.input_edit.toPlainText().strip()
        img = self.attached_image_b64

        if not text and not img:
            return

        if not text and img:
            text = "این تصویر را بررسی کن."

        self.input_edit.clear()
        self.remove_attached_image()

        # Add user message
        user_msg = ChatMessage(role="user", content=text, image_base64=img)
        self.current_messages.append(user_msg)
        save_chat_history(self.selected_agent.id, self.current_messages)
        self.render_chat_messages()

        # Lock UI & Start worker
        self.send_btn.setEnabled(False)
        self.attach_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.api_thread = ApiWorker(self.selected_agent, list(self.current_messages))
        self.api_thread.finished.connect(self.on_api_finished)
        self.api_thread.error.connect(self.on_api_error)
        self.api_thread.start()

    def on_api_finished(self, reply: str):
        self.progress_bar.setVisible(False)
        self.send_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)

        assistant_msg = ChatMessage(role="assistant", content=reply)
        self.current_messages.append(assistant_msg)
        if self.selected_agent:
            save_chat_history(self.selected_agent.id, self.current_messages)
        self.render_chat_messages()

    def on_api_error(self, err_text: str):
        self.progress_bar.setVisible(False)
        self.send_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)

        error_msg = ChatMessage(role="assistant", content=f"⚠️ {err_text}")
        self.current_messages.append(error_msg)
        if self.selected_agent:
            save_chat_history(self.selected_agent.id, self.current_messages)
        self.render_chat_messages()


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
