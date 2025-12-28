# -*- coding: utf-8 -*-
"""
Preset Manager Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QListWidget, QPushButton, QMessageBox, QFrame,
    QLineEdit, QPlainTextEdit, QInputDialog, QApplication
)
from PySide6.QtCore import Qt
from UI.theme import get_theme
from local_preset_manager import local_preset_manager
from network_manager import network_manager

class PresetManagerDialog(QDialog):
    """Integrated preset manager (Local, My Published, Online)"""
    def __init__(self, parent=None, current_data_callback=None, load_callback=None):
        super().__init__(parent)
        self.setWindowTitle("プリセットマネージャー")
        self.setFixedSize(800, 600)
        self.theme = get_theme()
        
        # Callbacks
        self.get_current_data = current_data_callback # Function returning current edit data
        self.on_load_data = load_callback # Function to apply loaded data
        
        self._setup_ui()
        self._refresh_local_list()
        
    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_dark}; color: {self.theme.text_primary};")
        layout = QVBoxLayout(self)
        
        # Header Status
        self.status_bar = QLabel("読み込み中...")
        self.status_bar.setStyleSheet(f"background: {self.theme.bg_card}; padding: 4px; border-radius: 4px; font-size: 11px;")
        layout.addWidget(self.status_bar)
        
        # Main Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {self.theme.border}; }}
            QTabBar::tab {{
                background: {self.theme.bg_card};
                color: {self.theme.text_secondary};
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {self.theme.bg_dark};
                color: {self.theme.primary};
                font-weight: bold;
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)
        
        # 1. Local Presets Tab
        self.local_tab = self._create_local_tab()
        self.tabs.addTab(self.local_tab, "ローカル保存")
        
        # 2. My Published Tab
        self.published_tab = self._create_published_tab()
        self.tabs.addTab(self.published_tab, "公開中")
        
        # 3. Online Library Tab
        self.online_tab = self._create_online_tab()
        self.tabs.addTab(self.online_tab, "オンライン")
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        # Footer
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 8px;")
        layout.addWidget(close_btn, 0, Qt.AlignRight)
        
        self._update_limits_display()

    def _create_local_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left: List
        list_container = QVBoxLayout()
        self.local_list = QListWidget()
        self.local_list.setStyleSheet(f"background: {self.theme.bg_card}; border: none;")
        self.local_list.itemClicked.connect(self._on_local_selected)
        list_container.addWidget(QLabel("保存済みプリセット (最大50件)"))
        list_container.addWidget(self.local_list)
        
        # Action Buttons (Save Current)
        save_btn = QPushButton("現在のエディットデータをローカルに保存")
        save_btn.setStyleSheet(f"background: {self.theme.success}; color: white; border: none; padding: 8px; font-weight: bold;")
        save_btn.clicked.connect(self._save_current_to_local)
        list_container.addWidget(save_btn)
        
        layout.addLayout(list_container, 2)
        
        # Right: Details (Editable)
        self.local_details = QWidget()
        self.local_details.setVisible(False)
        det_layout = QVBoxLayout(self.local_details)
        det_layout.setContentsMargins(16, 0, 0, 0)
        
        # Editable Name
        det_layout.addWidget(QLabel("プリセット名:"))
        self.local_name_edit = QLineEdit()
        self.local_name_edit.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; padding: 8px; font-size: 14px; font-weight: bold;")
        det_layout.addWidget(self.local_name_edit)
        
        # Editable Description
        det_layout.addWidget(QLabel("説明:"))
        self.local_desc_edit = QPlainTextEdit()
        self.local_desc_edit.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; padding: 8px;")
        self.local_desc_edit.setFixedHeight(120)
        det_layout.addWidget(self.local_desc_edit)
        
        # Update Button
        update_btn = QPushButton("変更を保存")
        update_btn.setStyleSheet(f"background: {self.theme.success}; color: white; padding: 8px; border: none; margin-top: 8px;")
        update_btn.clicked.connect(self._update_local_preset)
        det_layout.addWidget(update_btn)
        
        det_layout.addStretch()
        
        # Actions
        load_btn = QPushButton("ゲームに読み込む")
        load_btn.setStyleSheet(f"background: #ffffff; color: #000000; padding: 10px; border: none;")
        load_btn.clicked.connect(self._load_local_to_game)
        det_layout.addWidget(load_btn)
        
        pub_btn = QPushButton("オンラインに公開")
        pub_btn.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.primary}; border: 1px solid {self.theme.primary}; padding: 10px; margin-top: 8px;")
        pub_btn.clicked.connect(self._publish_local_preset)
        det_layout.addWidget(pub_btn)
        
        del_btn = QPushButton("削除")
        del_btn.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.error}; border: 1px solid {self.theme.error}; padding: 8px; margin-top: 8px;")
        del_btn.clicked.connect(self._delete_local_preset)
        det_layout.addWidget(del_btn)
        
        layout.addWidget(self.local_details, 1)
        
        return widget

    def _create_published_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.pub_status_lbl = QLabel("情報を取得中...")
        layout.addWidget(self.pub_status_lbl)
        
        self.pub_info_frame = QFrame()
        self.pub_info_frame.setVisible(False)
        self.pub_info_frame.setStyleSheet(f"background: {self.theme.bg_card}; border-radius: 8px; padding: 20px;")
        info_layout = QVBoxLayout(self.pub_info_frame)
        
        self.pub_name = QLabel()
        self.pub_name.setStyleSheet("font-size: 24px; font-weight: bold;")
        info_layout.addWidget(self.pub_name)
        
        self.pub_id = QLabel() 
        self.pub_id.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.pub_id.setStyleSheet(f"color: {self.theme.primary}; font-family: monospace; margin: 4px 0;")
        info_layout.addWidget(self.pub_id)
        
        self.pub_date = QLabel()
        info_layout.addWidget(self.pub_date)
        
        info_layout.addStretch()
        
        self.unpub_btn = QPushButton("公開を停止")
        self.unpub_btn.setStyleSheet(f"background: {self.theme.error}; color: white; border: none; border-radius: 0px; padding: 10px; font-weight: bold;")
        self.unpub_btn.clicked.connect(self._unpublish_preset)
        info_layout.addWidget(self.unpub_btn)
        
        layout.addWidget(self.pub_info_frame)
        layout.addStretch()
        
        refresh_btn = QPushButton("更新")
        refresh_btn.clicked.connect(self._refresh_published_tab)
        layout.addWidget(refresh_btn)
        
        return widget

    def _create_online_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left: List
        list_layout = QVBoxLayout()
        
        # ID Search
        id_search_layout = QHBoxLayout()
        self.id_search_edit = QLineEdit()
        self.id_search_edit.setPlaceholderText("プリセットIDで検索...")
        self.id_search_edit.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; padding: 6px;")
        id_search_layout.addWidget(self.id_search_edit)
        
        id_search_btn = QPushButton("検索")
        id_search_btn.setStyleSheet(f"background: #ffffff; color: #000000; border: none; padding: 6px 12px;")
        id_search_btn.clicked.connect(self._search_by_id)
        id_search_layout.addWidget(id_search_btn)
        list_layout.addLayout(id_search_layout)
        
        # Name/Description Search
        self.name_search_edit = QLineEdit()
        self.name_search_edit.setPlaceholderText("名前・説明で検索...")
        self.name_search_edit.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; padding: 6px; margin-top: 4px;")
        self.name_search_edit.textChanged.connect(self._filter_online_list)
        list_layout.addWidget(self.name_search_edit)
        
        # Sort Options
        from PySide6.QtWidgets import QComboBox
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("並び替え:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["公開日時 (新しい順)", "公開日時 (古い順)", "ダウンロード数 (多い順)"])
        self.sort_combo.setStyleSheet(f"background: {self.theme.bg_card}; padding: 4px;")
        self.sort_combo.currentIndexChanged.connect(self._sort_online_list)
        sort_layout.addWidget(self.sort_combo)
        list_layout.addLayout(sort_layout)
        
        self.online_list = QListWidget()
        self.online_list.setStyleSheet(f"background: {self.theme.bg_card}; border: none;")
        self.online_list.itemClicked.connect(self._on_online_selected)
        list_layout.addWidget(QLabel("プリセット一覧"))
        list_layout.addWidget(self.online_list)
        
        refresh_btn = QPushButton("リスト更新")
        refresh_btn.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 6px;")
        refresh_btn.clicked.connect(self._refresh_online_tab)
        list_layout.addWidget(refresh_btn)
        
        layout.addLayout(list_layout, 2)
        
        # Right: Details
        self.online_details = QWidget()
        self.online_details.setVisible(False)
        det_layout = QVBoxLayout(self.online_details)
        det_layout.setContentsMargins(16, 0, 0, 0)
        
        self.online_name = QLabel()
        self.online_name.setStyleSheet("font-size: 16px; font-weight: bold;")
        det_layout.addWidget(self.online_name)
        
        self.online_author = QLabel()
        self.online_author.setStyleSheet(f"color: {self.theme.primary};")
        det_layout.addWidget(self.online_author)
        
        self.online_desc = QLabel()
        self.online_desc.setWordWrap(True)
        self.online_desc.setStyleSheet(f"color: {self.theme.text_secondary}; margin: 8px 0;")
        det_layout.addWidget(self.online_desc)
        
        det_layout.addStretch()
        
        self.dl_btn = QPushButton("ダウンロード")
        self.dl_btn.setStyleSheet(f"background: #ffffff; color: #000000; padding: 10px; border: none; font-weight: bold;")
        self.dl_btn.clicked.connect(self._download_online_preset)
        det_layout.addWidget(self.dl_btn)
        
        layout.addWidget(self.online_details, 1)
        
        return widget

    # --- Logic ---

    def _update_limits_display(self):
        limits = network_manager.get_remaining_limits()
        self.status_bar.setText(f"本日の残り - 公開: {limits['publish']}回 / ダウンロード: {limits['load']}回")

    def _on_tab_changed(self, index):
        if index == 1:
            self._refresh_published_tab()
        elif index == 2:
            self._refresh_online_tab()
            
    # Local Logic
    
    def _refresh_local_list(self):
        self.local_list.clear()
        self.local_details.setVisible(False)
        try:
            presets = local_preset_manager.get_all_presets()
            for p in presets:
                self.local_list.addItem(f"{p['name']} ({p['updated_at'][:10]})")
            
            # Store data in list items (using user role or parallel list) ?
            # Simple approach: Store list of preset objects self.local_presets
            self.local_presets = presets
        except Exception as e:
            print(e)
            
    def _on_local_selected(self, item):
        idx = self.local_list.row(item)
        if idx >= 0 and idx < len(self.local_presets):
            p = self.local_presets[idx]
            self.current_local_preset = p
            
            self.local_name_edit.setText(p["name"])
            self.local_desc_edit.setPlainText(p.get("description", ""))
            self.local_details.setVisible(True)

    def _save_current_to_local(self):
        # Custom dialog with larger description input
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("ローカル保存")
        dialog.setFixedSize(400, 300)
        dialog.setStyleSheet(f"background: {self.theme.bg_dark}; color: {self.theme.text_primary};")
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("プリセット名:"))
        name_edit = QLineEdit()
        name_edit.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; padding: 8px;")
        layout.addWidget(name_edit)
        
        layout.addWidget(QLabel("説明 (任意):"))
        desc_edit = QPlainTextEdit()
        desc_edit.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; padding: 8px;")
        desc_edit.setFixedHeight(150)
        layout.addWidget(desc_edit)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(f"background: {self.theme.success}; color: white; padding: 8px;")
        save_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec() != QDialog.Accepted:
            return
            
        name = name_edit.text().strip()
        desc = desc_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "エラー", "プリセット名を入力してください。")
            return
        
        if self.get_current_data:
            try:
                data = self.get_current_data()
                success, msg = local_preset_manager.save_preset(data, name, desc)
                if success:
                    QMessageBox.information(self, "保存成功", "ローカルに保存しました。")
                    self._refresh_local_list()
                else:
                    QMessageBox.warning(self, "保存失敗", msg)
            except Exception as e:
                QMessageBox.critical(self, "エラー", str(e))

    def _update_local_preset(self):
        """Update the name and description of a local preset"""
        if not hasattr(self, 'current_local_preset'): return
        
        new_name = self.local_name_edit.text().strip()
        new_desc = self.local_desc_edit.toPlainText().strip()
        
        if not new_name:
            QMessageBox.warning(self, "エラー", "プリセット名を入力してください。")
            return
            
        success = local_preset_manager.update_preset_metadata(
            self.current_local_preset['filename'], 
            new_name, 
            new_desc
        )
        
        if success:
            QMessageBox.information(self, "保存成功", "変更を保存しました。")
            self._refresh_local_list()
        else:
            QMessageBox.warning(self, "エラー", "保存に失敗しました。")

    def _delete_local_preset(self):
        if not hasattr(self, 'current_local_preset'): return
        
        ret = QMessageBox.question(self, "削除確認", f"'{self.current_local_preset['name']}' を削除しますか？")
        if ret == QMessageBox.Yes:
            local_preset_manager.delete_preset(self.current_local_preset['filename'])
            self._refresh_local_list()

    def _load_local_to_game(self):
        if not hasattr(self, 'current_local_preset'): return
        
        ret = QMessageBox.question(self, "読み込み確認", "現在の編集データを上書きしますか？")
        if ret == QMessageBox.Yes:
            data = local_preset_manager.load_preset_data(self.current_local_preset['filename'])
            if data and "data" in data:
                if self.on_load_data:
                    self.on_load_data(data["data"])
                    QMessageBox.information(self, "読み込み完了", "データを適用しました。")
            else:
                QMessageBox.warning(self, "エラー", "データの読み込みに失敗しました。")

    def _publish_local_preset(self):
        if not hasattr(self, 'current_local_preset'): return
        
        # Check config
        if not self._check_firebase_config(): return
        
        limits = network_manager.get_remaining_limits()
        if limits['publish'] <= 0:
            QMessageBox.warning(self, "制限", "本日の公開回数制限に達しています。")
            return
            
        ret = QMessageBox.question(self, "公開確認", 
            f"'{self.current_local_preset['name']}' を公開しますか？\n\n"
            "※ あなたが既に公開しているプリセットがある場合、上書きされます。"
        )
        if ret != QMessageBox.Yes: return
        
        # Load full data
        full_data = local_preset_manager.load_preset_data(self.current_local_preset['filename'])
        if not full_data:
            QMessageBox.warning(self, "エラー", "ローカルデータの読み込みに失敗しました。")
            return
            
        try:
            name = full_data.get("name")
            desc = full_data.get("description")
            # Author input? Default to Unknown
            author, ok = QInputDialog.getText(self, "作成者名", "公開者名を入力してください:", text="Unknown")
            if not ok: return
            
            data_content = full_data.get("data", {})
            
            doc_id = network_manager.publish_preset(data_content, name, desc, author)
            
            QMessageBox.information(self, "公開成功", "プリセットを公開しました！\n公開タブで確認できます。")
            self._update_limits_display()
            self.tabs.setCurrentIndex(1) # Switch to Published tab
            
        except Exception as e:
            QMessageBox.critical(self, "公開失敗", str(e))

    # Published Logic
    
    def _refresh_published_tab(self):
        if not self._check_firebase_config(silent=True): 
            self.pub_status_lbl.setText("Firebase設定が必要です。")
            return
            
        self.pub_status_lbl.setText("取得中...")
        QApplication.processEvents()
        
        try:
            preset = network_manager.get_user_preset()
            if preset:
                self.pub_status_lbl.setVisible(False)
                self.pub_info_frame.setVisible(True)
                self.pub_name.setText(preset["name"])
                self.pub_id.setText(f"ID: {preset['id']}")
                self.pub_date.setText(f"公開日: {preset.get('created_at', '')}")
                self.current_published_id = preset["id"]
            else:
                self.pub_status_lbl.setText("現在公開中のプリセットはありません。")
                self.pub_status_lbl.setVisible(True)
                self.pub_info_frame.setVisible(False)
        except Exception as e:
            self.pub_status_lbl.setText(f"取得エラー: {e}")

    def _unpublish_preset(self):
        if not hasattr(self, 'current_published_id'): return
        
        ret = QMessageBox.question(self, "停止確認", "公開を停止しますか？")
        if ret == QMessageBox.Yes:
            try:
                network_manager.delete_preset(self.current_published_id)
                QMessageBox.information(self, "完了", "削除しました。")
                self._refresh_published_tab()
            except Exception as e:
                QMessageBox.warning(self, "エラー", str(e))

    # Online Logic
    
    def _refresh_online_tab(self):
        if not self._check_firebase_config(silent=True): return
        
        self.online_list.clear()
        self.online_details.setVisible(False)
        self.online_presets = []
        self.online_presets_raw = []  # Store raw data for filtering
        
        try:
            presets = network_manager.get_global_presets()
            self.online_presets_raw = presets
            self._apply_online_filters()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"一覧取得失敗: {e}")

    def _apply_online_filters(self):
        """Apply current search and sort filters to the online list"""
        if not hasattr(self, 'online_presets_raw'):
            return
            
        # Start with raw data
        filtered = list(self.online_presets_raw)
        
        # Filter by name/description search text
        search_text = self.name_search_edit.text().strip().lower()
        if search_text:
            filtered = [p for p in filtered if 
                        search_text in p.get('name', '').lower() or 
                        search_text in p.get('description', '').lower()]
        
        # Sort based on combo selection
        sort_idx = self.sort_combo.currentIndex()
        if sort_idx == 0:  # 公開日時 (新しい順)
            filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_idx == 1:  # 公開日時 (古い順)
            filtered.sort(key=lambda x: x.get('created_at', ''))
        elif sort_idx == 2:  # ダウンロード数 (多い順)
            filtered.sort(key=lambda x: x.get('download_count', 0), reverse=True)
        
        # Update list
        self.online_list.clear()
        for p in filtered:
            dl_count = p.get('download_count', 0)
            self.online_list.addItem(f"{p['name']} (by {p['author']}) - DL:{dl_count}")
        self.online_presets = filtered
        
    def _filter_online_list(self):
        """Filter online list by name/description search"""
        self._apply_online_filters()
        
    def _sort_online_list(self):
        """Sort online list by selected criteria"""
        self._apply_online_filters()
        
    def _search_by_id(self):
        """Search for a specific preset by ID"""
        preset_id = self.id_search_edit.text().strip()
        if not preset_id:
            QMessageBox.warning(self, "エラー", "IDを入力してください。")
            return
            
        try:
            result = network_manager.load_preset(preset_id)
            if result:
                # Found - show in details
                self.current_online_preset = {
                    'id': preset_id,
                    'name': result.get('name', 'Unknown'),
                    'author': result.get('author', 'Unknown'),
                    'description': result.get('description', ''),
                }
                self.online_name.setText(result.get('name', 'Unknown'))
                self.online_author.setText(f"作成者: {result.get('author', 'Unknown')}")
                self.online_desc.setText(result.get('description', ''))
                self.online_details.setVisible(True)
                QMessageBox.information(self, "検索成功", f"プリセットが見つかりました: {result.get('name')}")
            else:
                QMessageBox.warning(self, "検索結果", "指定されたIDのプリセットは見つかりませんでした。")
        except Exception as e:
            QMessageBox.warning(self, "検索エラー", f"検索に失敗しました: {e}")

    def _on_online_selected(self, item):
        idx = self.online_list.row(item)
        if idx >= 0 and idx < len(self.online_presets):
            p = self.online_presets[idx]
            self.current_online_preset = p
            
            self.online_name.setText(p["name"])
            self.online_author.setText(f"作成者: {p['author']}")
            self.online_desc.setText(p.get("description", ""))
            self.online_details.setVisible(True)
            
    def _download_online_preset(self):
        """Download online preset and save to local presets"""
        if not hasattr(self, 'current_online_preset'): return
        
        limits = network_manager.get_remaining_limits()
        if limits['load'] <= 0:
            QMessageBox.warning(self, "制限", "本日のダウンロード回数制限に達しています。")
            return

        ret = QMessageBox.question(self, "ダウンロード確認", "このプリセットをダウンロードしてローカルに保存しますか？")
        if ret != QMessageBox.Yes: return
        
        try:
            result = network_manager.load_preset(self.current_online_preset['id'])
            if result and "data" in result:
                # Save to local presets
                name = result.get('name', 'Downloaded Preset')
                desc = result.get('description', '')
                author = result.get('author', 'Unknown')
                
                success, msg = local_preset_manager.save_preset(
                    result["data"], 
                    f"{name} (by {author})",
                    desc
                )
                
                if success:
                    QMessageBox.information(self, "完了", f"プリセットをローカルに保存しました。\nローカルタブで確認できます。")
                    self._update_limits_display()
                else:
                    QMessageBox.warning(self, "エラー", f"保存に失敗しました: {msg}")
            else:
                QMessageBox.warning(self, "エラー", "データが空、または不正です。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"ダウンロード失敗: {e}")
            
    # Helpers
    
    def _check_firebase_config(self, silent=False):
        if network_manager.is_configured():
            return True
            
        if silent: return False
            
        # Ask for config
        project_id, ok = QInputDialog.getText(self, "設定", "Firebase Project ID:")
        if ok and project_id:
            network_manager.save_config(project_id, "")
            return True
        return False
