/**
 * 菜單管理共用模組
 * 供 admin.html 和 line-admin.html 共用
 */

class MenuManager {
  constructor(options) {
    // 必要配置
    this.fetchFn = options.fetchFn;              // API 請求函數 (authFetch / apiFetch)
    this.showNotification = options.showNotification;
    this.getStores = options.getStores;          // 取得店家列表函數
    this.onMenuSaved = options.onMenuSaved;      // 儲存成功後的回調

    // API 端點配置
    this.apiPrefix = options.apiPrefix || '/api/admin';
    this.groupCode = options.groupCode || null;  // LINE 管專用

    // 建立店家的配置
    this.createStoreEndpoint = options.createStoreEndpoint || null;
    this.canCreateStore = options.canCreateStore !== false;

    // 篩選可編輯店家
    this.filterEditableStores = options.filterEditableStores || (stores => stores);

    // 內部狀態
    this.selectedImage = null;
    this.recognitionResult = null;
    this.targetStoreId = null;
    this.newStoreName = null;
    this.menuDiff = null;
    this.existingMenu = null;
    this.isDiffMode = false;
    this.recognizedStoreInfo = null;  // AI 辨識出的店家資訊
    this.existingStoreInfo = null;    // 現有的店家資訊（用於比較）

    // DOM 元素 ID（可自訂）
    this.elements = {
      modal: 'menu-upload-modal',
      storeSelect: 'target-store-select',
      newStoreName: 'new-store-name-input',
      uploadStep: 'upload-step',
      recognizingStep: 'recognizing-step',
      resultStep: 'result-step',
      uploadPreview: 'upload-preview',
      uploadArea: 'upload-area',
      previewImage: 'preview-image',
      recognizeBtn: 'recognize-btn',
      imageInput: 'menu-image-input',
      resultWarnings: 'result-warnings',
      resultEditor: 'result-editor',
      ...options.elements
    };
  }

  // === 初始化 ===

  init() {
    this._bindEvents();
  }

  _bindEvents() {
    // 店家選擇變更
    const select = document.getElementById(this.elements.storeSelect);
    if (select) {
      select.addEventListener('change', (e) => this._onStoreSelectChange(e));
    }

    // 新店家名稱輸入
    const newStoreInput = document.getElementById(this.elements.newStoreName);
    if (newStoreInput) {
      newStoreInput.addEventListener('input', () => this._updateRecognizeBtn());
    }
  }

  // === Modal 控制 ===

  open() {
    const modal = document.getElementById(this.elements.modal);
    if (modal) modal.style.display = 'flex';

    this._populateStoreSelect();
    this._resetState();
  }

  close() {
    const modal = document.getElementById(this.elements.modal);
    if (modal) modal.style.display = 'none';
    this._resetState();
  }

  _resetState() {
    this.selectedImage = null;
    this.recognitionResult = null;
    this.targetStoreId = null;
    this.newStoreName = null;
    this.menuDiff = null;
    this.existingMenu = null;
    this.isDiffMode = false;
    this.recognizedStoreInfo = null;
    this.existingStoreInfo = null;

    this._showStep('upload');
    this._setElement(this.elements.uploadPreview, 'display', 'none');
    this._setElement(this.elements.uploadArea, 'display', 'block');
    this._setElement(this.elements.recognizeBtn, 'disabled', true);
    this._setElement('clear-image-btn', 'display', 'none');
    this._setInputValue(this.elements.imageInput, '');
    this._setInputValue(this.elements.storeSelect, '');
    this._setElement(this.elements.newStoreName, 'display', 'none');
    this._setInputValue(this.elements.newStoreName, '');
  }

  _populateStoreSelect() {
    const select = document.getElementById(this.elements.storeSelect);
    if (!select) return;

    const stores = this.filterEditableStores(this.getStores());

    select.innerHTML = '<option value="">-- 選擇現有店家 --</option>';
    if (this.canCreateStore) {
      select.innerHTML += '<option value="__new__">+ 新增店家</option>';
    }
    stores.forEach(store => {
      select.innerHTML += `<option value="${store.id}">${store.name}</option>`;
    });
  }

  // === 圖片處理 ===

  /**
   * 前端圖片壓縮（使用 Canvas API）
   * @param {File} file - 原始圖片檔案
   * @param {number} maxSize - 最大邊長（預設 1920px）
   * @param {number} quality - JPEG 品質（預設 0.85）
   * @returns {Promise<string>} - 壓縮後的 Data URL
   */
  async _compressImage(file, maxSize = 1920, quality = 0.85) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        let { width, height } = img;
        const originalSize = Math.max(width, height);

        // 如果圖片已經夠小，直接讀取原檔
        if (originalSize <= maxSize && file.size < 500 * 1024) {
          const reader = new FileReader();
          reader.onload = (e) => resolve(e.target.result);
          reader.onerror = reject;
          reader.readAsDataURL(file);
          URL.revokeObjectURL(img.src);
          return;
        }

        // 需要壓縮：計算新尺寸
        if (originalSize > maxSize) {
          const ratio = maxSize / originalSize;
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }

        // 使用 Canvas 壓縮
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        // 輸出為 JPEG
        const compressedDataUrl = canvas.toDataURL('image/jpeg', quality);
        URL.revokeObjectURL(img.src);

        console.log(`圖片壓縮: ${file.size} bytes → ~${Math.round(compressedDataUrl.length * 0.75)} bytes`);
        resolve(compressedDataUrl);
      };
      img.onerror = () => {
        URL.revokeObjectURL(img.src);
        reject(new Error('圖片載入失敗'));
      };
      img.src = URL.createObjectURL(file);
    });
  }

  async handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      this.showNotification('圖片大小不能超過 10MB', 'error');
      return;
    }

    try {
      // 前端壓縮圖片
      this.selectedImage = await this._compressImage(file);
      const previewImg = document.getElementById(this.elements.previewImage);
      if (previewImg) previewImg.src = this.selectedImage;
      this._setElement(this.elements.uploadPreview, 'display', 'block');
      this._setElement(this.elements.uploadArea, 'display', 'none');
      this._setElement('clear-image-btn', 'display', 'inline-block');
      this._updateRecognizeBtn();
    } catch (err) {
      console.error('圖片處理失敗:', err);
      this.showNotification('圖片處理失敗', 'error');
    }
  }

  clearImage() {
    this.selectedImage = null;
    this._setElement(this.elements.uploadPreview, 'display', 'none');
    this._setElement(this.elements.uploadArea, 'display', 'block');
    this._setElement('clear-image-btn', 'display', 'none');
    this._setInputValue(this.elements.imageInput, '');
    this._updateRecognizeBtn();
  }

  // === 辨識流程 ===

  async recognize() {
    const select = document.getElementById(this.elements.storeSelect);
    const newStoreInput = document.getElementById(this.elements.newStoreName);

    this.targetStoreId = select.value === '__new__' ? null : select.value;
    this.newStoreName = select.value === '__new__' ? (newStoreInput?.value.trim() || null) : null;

    // 保存現有店家資訊（用於差異比較）
    if (this.targetStoreId) {
      const stores = this.getStores();
      const store = stores.find(s => s.id === this.targetStoreId);
      if (store) {
        this.existingStoreInfo = {
          name: store.name || null,
          phone: store.phone || null,
          address: store.address || null,
          description: store.description || null,
        };
      }
    } else {
      this.existingStoreInfo = null;
    }

    this._showStep('recognizing');

    try {
      const blob = await fetch(this.selectedImage).then(r => r.blob());
      const formData = new FormData();
      formData.append('file', blob, 'menu.jpg');

      // 根據配置決定 API 端點
      let url;
      if (this.targetStoreId) {
        if (this.groupCode) {
          url = `${this.apiPrefix}/stores/by-code/${encodeURIComponent(this.groupCode)}/${this.targetStoreId}/menu/recognize`;
        } else {
          url = `${this.apiPrefix}/stores/${this.targetStoreId}/menu/recognize`;
        }
      } else {
        if (this.groupCode) {
          url = `${this.apiPrefix}/menu/recognize`;
        } else {
          url = `${this.apiPrefix}/menu/recognize`;
        }
      }

      const res = await this.fetchFn(url, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // 處理回應
      if (data.recognized_menu) {
        this.recognitionResult = data.recognized_menu;
        this.recognizedStoreInfo = data.recognized_menu.store_info || null;
        this.existingMenu = data.existing_menu;
        this.menuDiff = data.diff;

        this.isDiffMode = this.existingMenu && this.menuDiff &&
          (this.menuDiff.added.length > 0 || this.menuDiff.modified.length > 0 || this.menuDiff.removed.length > 0);

        if (this.isDiffMode) {
          this._showDiffPreview(this.menuDiff);
        } else {
          this._showResult(data.recognized_menu);
        }
      } else {
        this.recognitionResult = data;
        this.recognizedStoreInfo = data.store_info || null;
        this._showResult(data);
      }
    } catch (err) {
      console.error('辨識失敗:', err);
      this.showNotification('辨識失敗：' + err.message, 'error');
      this._showStep('upload');
    }
  }

  // === 儲存菜單 ===

  async save() {
    if (this.isDiffMode) {
      await this._saveDiff();
    } else {
      await this._saveNormal();
    }
  }

  async _saveNormal() {
    const categories = this._collectCategoriesFromDOM();

    if (categories.length === 0) {
      this.showNotification('無有效菜單內容可儲存', 'error');
      return;
    }

    try {
      let storeId = this.targetStoreId;

      // 新增店家
      if (!storeId) {
        if (!this.newStoreName) {
          this.showNotification('請選擇店家或輸入新店家名稱', 'error');
          return;
        }

        storeId = await this._createStore(this.newStoreName);
        if (!storeId) return;

        this.showNotification(`店家「${this.newStoreName}」已建立，正在儲存菜單...`);
      }

      // 收集店家資訊
      const storeInfo = this._collectStoreInfoFromDOM();

      // 儲存菜單
      let url;
      if (this.groupCode) {
        url = `${this.apiPrefix}/stores/by-code/${encodeURIComponent(this.groupCode)}/${storeId}/menu`;
      } else {
        url = `${this.apiPrefix}/stores/${storeId}/menu`;
      }

      const body = { categories };
      if (storeInfo) {
        body.store_info = storeInfo;
      }

      const res = await this.fetchFn(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        this.close();
        this.showNotification('菜單儲存成功！');
        if (this.onMenuSaved) this.onMenuSaved();
      } else {
        const data = await res.json();
        this.showNotification(data.detail || '儲存失敗', 'error');
      }
    } catch (err) {
      console.error('儲存菜單失敗:', err);
      this.showNotification('儲存失敗：' + err.message, 'error');
    }
  }

  async _saveDiff() {
    if (!this.targetStoreId) {
      this.showNotification('未選擇店家，請重新操作', 'error');
      return;
    }

    const applyItems = [];
    const removeItems = [];

    // 收集勾選項目
    document.querySelectorAll('.diff-checkbox[data-type="added"]:checked').forEach(cb => {
      const idx = parseInt(cb.dataset.idx);
      const item = this.menuDiff.added[idx];
      if (item) applyItems.push(item);
    });

    document.querySelectorAll('.diff-checkbox[data-type="modified"]:checked').forEach(cb => {
      const idx = parseInt(cb.dataset.idx);
      const item = this.menuDiff.modified[idx];
      if (item) applyItems.push(item.new);
    });

    document.querySelectorAll('.diff-checkbox[data-type="removed"]:checked').forEach(cb => {
      const idx = parseInt(cb.dataset.idx);
      const item = this.menuDiff.removed[idx];
      if (item) removeItems.push(item.name);
    });

    if (applyItems.length === 0 && removeItems.length === 0) {
      this.showNotification('請至少選擇一項變更', 'error');
      return;
    }

    try {
      // 收集店家資訊
      const storeInfo = this._collectStoreInfoFromDOM();

      let url;
      if (this.groupCode) {
        url = `${this.apiPrefix}/stores/by-code/${encodeURIComponent(this.groupCode)}/${this.targetStoreId}/menu/save`;
      } else {
        url = `${this.apiPrefix}/stores/${this.targetStoreId}/menu/save`;
      }

      const body = {
        diff_mode: true,
        apply_items: applyItems,
        remove_items: removeItems,
      };
      if (storeInfo) {
        body.store_info = storeInfo;
      }

      const res = await this.fetchFn(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        this.close();
        this.showNotification('菜單已更新！');
        if (this.onMenuSaved) this.onMenuSaved();
      } else {
        const data = await res.json();
        this.showNotification(data.detail || '套用失敗', 'error');
      }
    } catch (err) {
      console.error('套用變更失敗:', err);
      this.showNotification('套用失敗', 'error');
    }
  }

  async _createStore(name) {
    try {
      let url;
      if (this.groupCode) {
        url = `${this.apiPrefix}/stores/by-code/${encodeURIComponent(this.groupCode)}`;
      } else {
        url = `${this.apiPrefix}/stores`;
      }

      const body = { name };
      if (!this.groupCode) {
        body.scope = 'global';
      }

      const res = await this.fetchFn(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || '建立店家失敗');
      }

      const storeData = await res.json();
      return storeData.id;
    } catch (err) {
      this.showNotification('建立店家失敗：' + err.message, 'error');
      return null;
    }
  }

  // === 編輯現有菜單 ===

  async editExisting(storeId) {
    this.targetStoreId = storeId;
    this.newStoreName = null;

    try {
      let url;
      if (this.groupCode) {
        url = `${this.apiPrefix}/stores/by-code/${encodeURIComponent(this.groupCode)}/${storeId}/menu`;
      } else {
        url = `${this.apiPrefix}/stores/${storeId}/menu/compare`;
      }

      const res = await this.fetchFn(url);
      const menu = await res.json();

      this.recognitionResult = menu;

      // 從 stores 列表中取得現有店家資訊
      const stores = this.getStores();
      const store = stores.find(s => s.id === storeId);
      if (store) {
        this.recognizedStoreInfo = {
          name: store.name || null,
          phone: store.phone || null,
          address: store.address || null,
          description: store.description || null,
        };
      } else {
        this.recognizedStoreInfo = null;
      }

      const modal = document.getElementById(this.elements.modal);
      if (modal) modal.style.display = 'flex';

      // 填充店家下拉選單並選中當前店家
      this._populateStoreSelect();
      const select = document.getElementById(this.elements.storeSelect);
      if (select) select.value = storeId;

      this._showStep('result');
      this._showResult(this.recognitionResult);
    } catch (err) {
      console.error('載入菜單失敗:', err);
      this.showNotification('載入菜單失敗', 'error');
    }
  }

  // === UI 渲染 ===

  _showStep(step) {
    this._setElement(this.elements.uploadStep, 'display', step === 'upload' ? 'block' : 'none');
    this._setElement(this.elements.recognizingStep, 'display', step === 'recognizing' ? 'block' : 'none');
    this._setElement(this.elements.resultStep, 'display', step === 'result' ? 'block' : 'none');
  }

  _showResult(menu) {
    this._showStep('result');

    // 清空警告區（不再用於店家資訊）
    const warningsEl = document.getElementById(this.elements.resultWarnings);
    if (warningsEl) {
      // 只顯示警告訊息
      if (menu.warnings && menu.warnings.length > 0) {
        warningsEl.innerHTML = `
          <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 10px; margin-bottom: 15px; border-radius: 4px;">
            <strong>⚠️ 注意事項：</strong>
            <ul style="margin: 5px 0 0 20px; padding: 0;">
              ${menu.warnings.map(w => `<li>${w}</li>`).join('')}
            </ul>
          </div>
        `;
      } else {
        warningsEl.innerHTML = '';
      }
    }

    const editor = document.getElementById(this.elements.resultEditor);
    if (!editor) return;

    // 左右兩欄佈局：左邊菜單、右邊店家資訊+按鈕
    let html = '<div class="result-two-columns">';

    // 左欄：菜單內容
    html += '<div class="result-left-column">';

    if (!menu.categories || menu.categories.length === 0) {
      html += '<div class="orders-empty">未辨識到菜單內容</div>';
    } else {
      menu.categories.forEach((category, catIdx) => {
        html += `
          <div class="result-category" data-cat-idx="${catIdx}">
            <div class="result-category-header">
              <input type="text" class="cat-name-input" value="${this._escapeHtml(category.name)}" data-cat-idx="${catIdx}">
            </div>
            <div class="result-items" id="cat-items-${catIdx}">
        `;

        if (category.items) {
          category.items.forEach((item, itemIdx) => {
            html += this._renderItemRow(item, catIdx, itemIdx);
          });
        }

        html += `
            </div>
            <button class="btn btn-sm" onclick="menuManager.addItem(${catIdx})">+ 新增品項</button>
          </div>
        `;
      });

      html += '<button class="btn btn-sm" style="margin-top: 15px;" onclick="menuManager.addCategory()">+ 新增分類</button>';
    }

    html += '</div>'; // end result-left-column

    // 右欄：店家資訊 + 按鈕
    html += '<div class="result-right-column">';

    // 店家資訊區塊（含差異比較）
    html += this._renderStoreInfoSection();

    // 按鈕區塊
    html += `
      <div class="result-actions-vertical">
        <button class="btn btn-primary" id="save-menu-btn" onclick="menuManager.save()">💾 確認並儲存</button>
        <button class="btn btn-secondary" onclick="menuManager.backToUpload()">🔄 重新上傳</button>
      </div>
    `;

    html += '</div>'; // end result-right-column
    html += '</div>'; // end result-two-columns

    editor.innerHTML = html;
  }

  _renderItemRow(item, catIdx, itemIdx) {
    return `
      <div class="result-item" data-cat-idx="${catIdx}" data-item-idx="${itemIdx}">
        <div class="item-main-row">
          <input type="text" class="item-name" value="${this._escapeHtml(item.name || '')}" placeholder="品名">
          <input type="number" class="item-price" value="${item.price || 0}" placeholder="價格">
          <input type="text" class="item-desc" value="${this._escapeHtml(item.description || '')}" placeholder="說明">
          <button class="btn btn-danger btn-sm" onclick="menuManager.removeItem(this)">✕</button>
        </div>
      </div>
    `;
  }

  _showDiffPreview(diff) {
    this._showStep('result');

    // 清空警告區
    const warningsEl = document.getElementById(this.elements.resultWarnings);
    if (warningsEl) {
      warningsEl.innerHTML = '';
    }

    const editor = document.getElementById(this.elements.resultEditor);
    if (!editor) return;

    // 左右兩欄佈局
    let html = '<div class="result-two-columns">';

    // 左欄：差異預覽
    html += '<div class="result-left-column">';
    html += '<div class="diff-preview">';

    // 新增品項
    if (diff.added.length > 0) {
      html += this._renderDiffSection('added', '✅ 新增品項', '#28a745', '#d4edda', '🟢', diff.added);
    }

    // 修改品項
    if (diff.modified.length > 0) {
      html += this._renderDiffSection('modified', '⚠️ 修改品項', '#856404', '#fff3cd', '🟡', diff.modified);
    }

    // 刪除品項
    if (diff.removed.length > 0) {
      html += this._renderDiffSection('removed', '❌ 刪除品項', '#dc3545', '#f8d7da', '🔴', diff.removed);
    }

    // 未變更品項（可展開）
    if (diff.unchanged && diff.unchanged.length > 0) {
      html += `
        <div class="diff-section" style="margin-bottom: 15px; border: 1px solid #ccc; border-radius: 4px; padding: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <strong style="color: #666;">📋 未變更品項 (${diff.unchanged.length})</strong>
            <button class="btn btn-sm" onclick="menuManager.toggleUnchanged()">
              <span id="unchanged-toggle">▶</span> 展開
            </button>
          </div>
          <div class="diff-items" id="unchanged-items" style="display: none;">
      `;
      diff.unchanged.forEach(item => {
        html += `
          <div style="padding: 5px 10px; background: #f5f5f5; margin-bottom: 5px; border-radius: 4px; color: #666;">
            ${this._escapeHtml(item.name)} - $${item.price || 0}
          </div>
        `;
      });
      html += '</div></div>';
    }

    html += '</div>'; // end diff-preview
    html += '</div>'; // end result-left-column

    // 右欄：店家資訊 + 按鈕
    html += '<div class="result-right-column">';

    // 店家資訊區塊（含差異比較）
    html += this._renderStoreInfoSection();

    // 按鈕區塊
    html += `
      <div class="result-actions-vertical">
        <button class="btn btn-primary" id="save-menu-btn" onclick="menuManager.save()">💾 套用變更</button>
        <button class="btn btn-secondary" onclick="menuManager.backToUpload()">🔄 重新上傳</button>
      </div>
    `;

    html += '</div>'; // end result-right-column
    html += '</div>'; // end result-two-columns

    editor.innerHTML = html;
  }

  _renderStoreInfoSection() {
    const newInfo = this.recognizedStoreInfo || {};
    const oldInfo = this.existingStoreInfo || {};
    const hasExisting = this.existingStoreInfo !== null;

    // 定義欄位
    const fields = [
      { key: 'name', label: '店名', type: 'input', placeholder: '店家名稱' },
      { key: 'phone', label: '電話', type: 'input', placeholder: '電話號碼' },
      { key: 'address', label: '地址', type: 'input', placeholder: '地址' },
      { key: 'description', label: '說明', type: 'textarea', placeholder: '營業時間、特色等' },
    ];

    let html = '<div class="store-info-section">';
    html += '<div class="store-info-title">🏪 店家資訊</div>';
    html += '<div class="store-info-form">';

    fields.forEach(field => {
      const oldVal = oldInfo[field.key] || '';
      const newVal = newInfo[field.key] || '';
      const hasChange = hasExisting && oldVal !== newVal;
      const displayVal = newVal || oldVal; // 優先顯示新值，沒有則顯示舊值

      html += '<div class="form-group">';

      // 標籤（含變更標記）
      if (hasChange) {
        html += `<label>${field.label} <span class="store-info-changed">⚠️ 有變更</span></label>`;
      } else {
        html += `<label>${field.label}</label>`;
      }

      // 顯示變更前後的值（如果有變更）
      if (hasChange) {
        const oldDisplay = oldVal || '(空)';
        const newDisplay = newVal || '(清除)';
        html += `<div class="store-info-diff">
          <span class="old-value">${this._escapeHtml(oldDisplay)}</span>
          <span class="diff-arrow">→</span>
          <span class="new-value">${this._escapeHtml(newDisplay)}</span>
        </div>`;
      }

      // 輸入欄位
      if (field.type === 'textarea') {
        html += `<textarea id="store-info-${field.key}" placeholder="${field.placeholder}" rows="3">${this._escapeHtml(displayVal)}</textarea>`;
      } else {
        html += `<input type="text" id="store-info-${field.key}" value="${this._escapeHtml(displayVal)}" placeholder="${field.placeholder}">`;
      }

      html += '</div>';
    });

    html += '</div></div>';
    return html;
  }

  _renderDiffSection(type, title, titleColor, bgColor, icon, items) {
    let html = `
      <div class="diff-section" style="margin-bottom: 15px; border: 1px solid ${titleColor}; border-radius: 4px; padding: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <strong style="color: ${titleColor};">${title} (${items.length})</strong>
          <label><input type="checkbox" checked onchange="menuManager.toggleDiffSection(this, '${type}')"> 全選</label>
        </div>
        <div class="diff-items">
    `;

    items.forEach((item, idx) => {
      let display;
      if (type === 'modified') {
        const oldPrice = item.old.price || 0;
        const newPrice = item.new.price || 0;
        const priceChange = oldPrice !== newPrice ? `$${oldPrice} → $${newPrice}` : `$${newPrice}`;
        display = `${icon} ${this._escapeHtml(item.new.name)} <span style="color: #666;">${priceChange}</span>`;
      } else {
        const priceDisplay = item.variants && item.variants.length > 0
          ? item.variants.map(v => `${v.name} $${v.price}`).join(' / ')
          : `$${item.price || 0}`;
        display = `${icon} ${this._escapeHtml(item.name)} <span style="color: #666;">${priceDisplay}</span>`;
        if (item.category) {
          display += ` <span style="color: #999; font-size: 0.9em;">[${this._escapeHtml(item.category)}]</span>`;
        }
      }

      html += `
        <div style="padding: 5px 10px; background: ${bgColor}; margin-bottom: 5px; border-radius: 4px;">
          <label style="display: flex; align-items: center; gap: 10px;">
            <input type="checkbox" class="diff-checkbox" data-type="${type}" data-idx="${idx}" checked>
            <span>${display}</span>
          </label>
        </div>
      `;
    });

    html += '</div></div>';
    return html;
  }

  // === DOM 操作輔助 ===

  addItem(catIdx) {
    const container = document.getElementById(`cat-items-${catIdx}`);
    if (!container) return;

    const itemIdx = container.querySelectorAll('.result-item').length;
    const html = this._renderItemRow({}, catIdx, itemIdx);
    container.insertAdjacentHTML('beforeend', html);
  }

  addCategory() {
    const editor = document.getElementById(this.elements.resultEditor);
    if (!editor) return;

    const categories = editor.querySelectorAll('.result-category');
    const catIdx = categories.length;

    const html = `
      <div class="result-category" data-cat-idx="${catIdx}">
        <div class="result-category-header">
          <input type="text" class="cat-name-input" value="新分類" data-cat-idx="${catIdx}">
        </div>
        <div class="result-items" id="cat-items-${catIdx}"></div>
        <button class="btn btn-sm" onclick="menuManager.addItem(${catIdx})">+ 新增品項</button>
      </div>
    `;

    const addCatBtn = editor.querySelector(':scope > button:last-child');
    if (addCatBtn) {
      addCatBtn.insertAdjacentHTML('beforebegin', html);
    }
  }

  removeItem(btn) {
    const row = btn.closest('.result-item');
    if (row) row.remove();
  }

  toggleDiffSection(checkbox, type) {
    const checked = checkbox.checked;
    document.querySelectorAll(`.diff-checkbox[data-type="${type}"]`).forEach(cb => {
      cb.checked = checked;
    });
  }

  toggleUnchanged() {
    const items = document.getElementById('unchanged-items');
    const toggle = document.getElementById('unchanged-toggle');
    if (items && toggle) {
      if (items.style.display === 'none') {
        items.style.display = 'block';
        toggle.textContent = '▼';
      } else {
        items.style.display = 'none';
        toggle.textContent = '▶';
      }
    }
  }

  backToUpload() {
    this._showStep('upload');
    this.clearImage();
    // 重新填充店家下拉選單（可能有新增的店家）
    this._populateStoreSelect();
    // 保留原本選擇的店家
    if (this.targetStoreId) {
      const select = document.getElementById(this.elements.storeSelect);
      if (select) select.value = this.targetStoreId;
    }
  }

  // === 內部輔助 ===

  _onStoreSelectChange(e) {
    const newStoreInput = document.getElementById(this.elements.newStoreName);
    if (newStoreInput) {
      newStoreInput.style.display = e.target.value === '__new__' ? 'block' : 'none';
      if (e.target.value !== '__new__') {
        newStoreInput.value = '';
      }
    }
    this._updateRecognizeBtn();
  }

  _updateRecognizeBtn() {
    const select = document.getElementById(this.elements.storeSelect);
    const newStoreInput = document.getElementById(this.elements.newStoreName);
    const hasStore = select?.value && (select.value !== '__new__' || newStoreInput?.value.trim());
    this._setElement(this.elements.recognizeBtn, 'disabled', !this.selectedImage || !hasStore);
  }

  _collectCategoriesFromDOM() {
    const categories = [];
    document.querySelectorAll('.result-category').forEach(catEl => {
      const catName = catEl.querySelector('.cat-name-input')?.value.trim() || '未命名';
      const items = [];

      catEl.querySelectorAll('.result-item').forEach(itemEl => {
        const name = itemEl.querySelector('.item-name')?.value.trim();
        const price = parseInt(itemEl.querySelector('.item-price')?.value) || 0;
        const desc = itemEl.querySelector('.item-desc')?.value.trim() || '';

        if (name) {
          items.push({ name, price, description: desc });
        }
      });

      if (items.length > 0) {
        categories.push({ name: catName, items });
      }
    });
    return categories;
  }

  _collectStoreInfoFromDOM() {
    // 收集店家資訊表單的值
    const nameEl = document.getElementById('store-info-name');
    const phoneEl = document.getElementById('store-info-phone');
    const addressEl = document.getElementById('store-info-address');
    const descEl = document.getElementById('store-info-description');

    // 如果沒有任何店家資訊欄位，回傳 null
    if (!nameEl && !phoneEl && !addressEl && !descEl) {
      return null;
    }

    const name = nameEl?.value.trim() || null;
    const phone = phoneEl?.value.trim() || null;
    const address = addressEl?.value.trim() || null;
    const description = descEl?.value.trim() || null;

    // 如果所有欄位都是空的，回傳 null
    if (!name && !phone && !address && !description) {
      return null;
    }

    return { name, phone, address, description };
  }

  _setElement(id, prop, value) {
    const el = document.getElementById(id);
    if (el) {
      if (prop === 'display') {
        el.style.display = value;
      } else if (prop === 'disabled') {
        el.disabled = value;
      }
    }
  }

  _setInputValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
  }

  _escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;');
  }
}

// 全域變數，供 HTML onclick 使用
let menuManager = null;
