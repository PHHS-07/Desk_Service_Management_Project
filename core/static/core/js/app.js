document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.querySelector('#sidebar');
    const toggle = document.querySelector('[data-toggle-sidebar]');
    const loader = document.getElementById('app-loader');

    if (loader) {
        loader.hidden = true;
        window.addEventListener('pageshow', () => {
            loader.hidden = true;
        });
    }

    // Theme Toggle Logic
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        // Set initial state
        themeToggle.checked = document.documentElement.getAttribute('data-theme') === 'dark';
        
        themeToggle.addEventListener('change', () => {
            if (themeToggle.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
            }
        });
    }

    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    const confirmDialog = document.getElementById('confirm-dialog');
    const confirmMessage = document.getElementById('confirm-dialog-message');
    let pendingForm = null;

    document.querySelectorAll('form[data-confirm]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            const message = form.getAttribute('data-confirm');
            if (message && confirmDialog) {
                event.preventDefault();
                pendingForm = form;
                confirmMessage.textContent = message;
                confirmDialog.hidden = false;
            }
        });
    });

    document.querySelectorAll('[data-dialog-cancel]').forEach((button) => {
        button.addEventListener('click', () => {
            pendingForm = null;
            if (confirmDialog) confirmDialog.hidden = true;
        });
    });

    document.querySelector('[data-dialog-confirm]')?.addEventListener('click', () => {
        const form = pendingForm;
        pendingForm = null;
        if (confirmDialog) confirmDialog.hidden = true;
        if (form) {
            form.removeAttribute('data-confirm');
            form.submit();
        }
    });

    document.querySelectorAll('.sidebar-nav a[href^="#"]').forEach((link) => {
        link.addEventListener('click', () => {
            if (sidebar) {
                sidebar.classList.remove('open');
            }
        });
    });

    document.querySelectorAll('[data-filter-select]').forEach((input) => {
        const select = document.getElementById(input.getAttribute('data-filter-select'));
        if (!select) {
            return;
        }

        input.addEventListener('input', () => {
            const query = input.value.trim().toLowerCase();
            Array.from(select.options).forEach((option) => {
                const matches = option.textContent.toLowerCase().includes(query);
                option.hidden = query && !matches;
            });
        });
    });

    // Debounce helper
    const debounce = (fn, wait = 450) => {
        let t = null;
        return (...args) => {
            if (t) clearTimeout(t);
            t = setTimeout(() => fn(...args), wait);
        };
    };

    // Inline feedback element helper
    const showInlineFeedback = (input, text, type) => {
        let el = input.parentNode.querySelector('.inline-feedback');
        if (!el) {
            el = document.createElement('div');
            el.className = 'inline-feedback';
            input.parentNode.appendChild(el);
        }
        el.textContent = text || '';
        el.classList.remove('success','error','warning');
        if (type) el.classList.add(type);
        el.hidden = !text;
    };

    // Username availability check (debounced)
    const checkUsername = debounce(async (input) => {
        const v = (input.value || '').trim();
        showInlineFeedback(input, 'Checking...', 'warning');
        if (!v) { input.classList.remove('username-available','username-taken'); showInlineFeedback(input, ''); input.setCustomValidity(''); return; }
        try {
            const res = await fetch(`/ajax/username-available/?username=${encodeURIComponent(v)}`);
            if (!res.ok) throw new Error('network');
            const data = await res.json();
            if (data.available) {
                input.classList.remove('username-taken');
                input.classList.add('username-available');
                showInlineFeedback(input, 'Username available', 'success');
                input.setCustomValidity('');
            } else {
                input.classList.remove('username-available');
                input.classList.add('username-taken');
                showInlineFeedback(input, 'Username already taken', 'error');
                input.setCustomValidity('Username already taken');
            }
        } catch (e) {
            showInlineFeedback(input, 'Error checking username', 'warning');
            input.setCustomValidity('');
        }
    }, 450);

    // Input sanitizers: mobile digits only, name letters only, email trim
    const setupInputSanitizers = () => {
        document.querySelectorAll('input[name="mobile_number"], input[id$="mobile_number"]').forEach((input) => {
            input.maxLength = 10;
            input.addEventListener('keypress', (ev) => {
                const ch = ev.key;
                if (!/\d/.test(ch)) ev.preventDefault();
            });
            input.addEventListener('input', () => {
                const cleaned = (input.value || '').replace(/\D/g, '').slice(0,10);
                if (cleaned !== input.value) input.value = cleaned;
            });
        });

        document.querySelectorAll('input[name="name"], input[name="first_name"], input[name="last_name"]').forEach((input) => {
            input.addEventListener('keypress', (ev) => {
                const ch = ev.key;
                if (!/^[a-zA-Z \-']$/.test(ch)) ev.preventDefault();
            });
            input.addEventListener('input', () => {
                const cleaned = (input.value || '').replace(/[^a-zA-Z \-']/g, '');
                if (cleaned !== input.value) input.value = cleaned;
            });
        });

        document.querySelectorAll('input[type="email"]').forEach((input) => {
            input.addEventListener('input', () => {
                // basic trim and prevent leading/trailing spaces
                const v = (input.value || '').replace(/\s+/g, '');
                if (v !== input.value) input.value = v;
            });
        });
    };

    // Wire up username availability on username inputs and prevent submit on taken
    document.querySelectorAll('input[name="username"], input[id$="username"]').forEach((input) => {
        const form = input.closest('form');
        // skip username availability checks on forms that opt-out (e.g., login form)
        if (form && form.hasAttribute('data-no-username-check')) return;
        input.addEventListener('input', () => checkUsername(input));
        input.addEventListener('blur', () => checkUsername(input));
    });
    document.querySelectorAll('form').forEach((form) => {
        form.addEventListener('submit', (ev) => {
            const taken = form.querySelector('input.username-taken');
            if (taken) {
                ev.preventDefault();
                showInlineFeedback(taken, 'Please choose a different username before submitting.', 'error');
                taken.focus();
            }
        });
    });

    setupInputSanitizers();

    document.querySelectorAll('[data-toggle-panel]').forEach((button) => {
        button.addEventListener('click', () => {
            const panel = document.getElementById(button.getAttribute('data-toggle-panel'));
            if (panel) {
                panel.hidden = !panel.hidden;
            }
        });
    });

    document.querySelectorAll('[data-multi-select]').forEach((wrap) => {
        const toggle = wrap.querySelector('[data-multi-toggle]');
        const menu = wrap.querySelector('[data-multi-menu]');
        const label = wrap.querySelector('[data-multi-label]');
        if (!toggle || !menu || !label) return;

        // Ensure proper hidden state
        menu.hidden = true;

        // Helper: Generate Avatar initials and color
        const getAvatar = (name) => {
            const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '?';
            const colors = ['#f87171', '#fb923c', '#fbbf24', '#a3e635', '#4ade80', '#34d399', '#2dd4bf', '#38bdf8', '#60a5fa', '#818cf8', '#a78bfa', '#c084fc', '#e879f9', '#f472b6', '#fb7185'];
            const charCodeSum = name.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
            const color = colors[charCodeSum % colors.length];
            return `<div class="ms-avatar" style="background-color: ${color}">${initials}</div>`;
        };

        // Extract native inputs
        const nativeInputs = Array.from(menu.querySelectorAll('input[type="checkbox"], input[type="radio"]'));
        
        // Hide native inputs container (either a ul or div block)
        nativeInputs.forEach(input => {
            input.removeAttribute('required'); // Prevent HTML5 validation from blocking hidden inputs
            const container = input.closest('ul') || input.closest('div[id^="id_"]');
            if (container) container.style.display = 'none';
        });

        // Setup Custom List Container
        const searchWrap = document.createElement('div');
        searchWrap.className = 'ms-search-wrap';
        const searchInput = document.createElement('input');
        searchInput.type = 'search';
        searchInput.className = 'ms-search';
        searchInput.placeholder = 'Search...';
        searchWrap.appendChild(searchInput);
        
        const selectAllWrap = document.createElement('div');
        selectAllWrap.className = 'ms-select-all';
        selectAllWrap.innerHTML = `
            <div class="ms-check"></div>
            <span style="flex:1">Select All</span>
        `;
        
        const listContainer = document.createElement('div');
        listContainer.className = 'ms-list';

        const customItems = [];

        if (nativeInputs.length === 0) {
            listContainer.innerHTML = '<div class="ms-item"><span class="ms-item-label" style="color: var(--muted); padding: 8px;">No options available</span></div>';
        }

        nativeInputs.forEach((nativeInput) => {
            const nativeLabel = wrap.querySelector(`label[for="${nativeInput.id}"]`) || nativeInput.closest('label');
            const name = nativeLabel ? nativeLabel.textContent.trim() : nativeInput.value;
            
            const item = document.createElement('div');
            item.className = 'ms-item';
            item.innerHTML = `
                ${getAvatar(name)}
                <span class="ms-item-label">${name}</span>
                <div class="ms-check"></div>
            `;
            
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                nativeInput.checked = !nativeInput.checked;
                nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
            });
            
            listContainer.appendChild(item);
            customItems.push({ item, nativeInput, name });
        });

        // Prepend custom elements to menu
        if (nativeInputs.length > 0) {
            const container = nativeInputs[0].closest('ul') || nativeInputs[0].closest('div[id^="id_"]');
            if (container && container.parentNode === menu) {
                menu.insertBefore(listContainer, container);
            } else {
                menu.appendChild(listContainer);
            }
        } else {
            menu.appendChild(listContainer);
        }
        
        if (nativeInputs.length > 0) {
            menu.insertBefore(selectAllWrap, listContainer);
            menu.insertBefore(searchWrap, selectAllWrap);
        }

        // Search Logic
        searchInput.addEventListener('input', () => {
            const q = searchInput.value.trim().toLowerCase();
            customItems.forEach(({ item, name }) => {
                item.style.display = (q === '' || name.toLowerCase().includes(q)) ? 'flex' : 'none';
            });
            updateSelectAllState();
        });

        // Select All Logic
        selectAllWrap.addEventListener('click', (e) => {
            e.stopPropagation();
            const visibleItems = customItems.filter(ci => ci.item.style.display !== 'none');
            const allChecked = visibleItems.every(ci => ci.nativeInput.checked);
            
            visibleItems.forEach(ci => {
                if (ci.nativeInput.checked === allChecked) {
                    ci.nativeInput.checked = !allChecked;
                    ci.nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        });

        const updateSelectAllState = () => {
            const visibleItems = customItems.filter(ci => ci.item.style.display !== 'none');
            const allChecked = visibleItems.length > 0 && visibleItems.every(ci => ci.nativeInput.checked);
            selectAllWrap.classList.toggle('selected', allChecked);
        };

        // Render function (Updates UI based on native inputs)
        const refresh = () => {
            const checkedInputs = nativeInputs.filter(n => n.checked);
            const selectedCount = checkedInputs.length;
            label.innerHTML = '';
            
            customItems.forEach(({ item, nativeInput }) => {
                item.classList.toggle('selected', nativeInput.checked);
            });
            
            if (selectedCount === 0) {
                label.innerHTML = '<span class="placeholder">Select items...</span>';
            } else {
                checkedInputs.slice(0, 2).forEach((nativeInput) => {
                    const nativeLabel = wrap.querySelector(`label[for="${nativeInput.id}"]`) || nativeInput.closest('label');
                    const name = nativeLabel ? nativeLabel.textContent.trim() : nativeInput.value;
                    const pill = document.createElement('span');
                    pill.className = 'ms-pill';
                    pill.innerHTML = `
                        ${getAvatar(name)}
                        ${name}
                        <button type="button" class="ms-pill-remove" aria-label="Remove">&times;</button>
                    `;
                    pill.querySelector('.ms-pill-remove').addEventListener('click', (e) => {
                        e.stopPropagation();
                        nativeInput.checked = false;
                        nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                    label.appendChild(pill);
                });
                
                if (selectedCount > 2) {
                    const more = document.createElement('span');
                    more.className = 'ms-pill';
                    more.style.padding = '2px 8px';
                    more.style.fontWeight = '700';
                    more.textContent = `+${selectedCount - 2} more`;
                    label.appendChild(more);
                }
            }
            updateSelectAllState();
        };

        // Event Listeners
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = !menu.hidden;
            // Close all others
            document.querySelectorAll('[data-multi-menu]').forEach(m => m.hidden = true);
            document.querySelectorAll('.multi-select').forEach(m => m.classList.remove('open'));
            
            if (!isOpen) {
                menu.hidden = false;
                wrap.classList.add('open');
                if (nativeInputs.length > 0) searchInput.focus();
            }
        });

        menu.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        nativeInputs.forEach((c) => c.addEventListener('change', refresh));
        
        document.addEventListener('click', (event) => {
            if (!wrap.contains(event.target)) {
                menu.hidden = true;
                wrap.classList.remove('open');
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !menu.hidden) {
                menu.hidden = true;
                wrap.classList.remove('open');
                toggle.focus();
            }
        });

        refresh();
    });

    document.querySelectorAll('.sidebar-nav a').forEach((link) => {
        link.addEventListener('click', () => {
            if (loader) loader.hidden = false;
        });
    });

    // Password visibility toggle and autofill generation for admin add/edit forms
    const setupPasswordUI = () => {
        // attach toggles to all password inputs
        document.querySelectorAll('input[type="password"]').forEach((input) => {
            if (input.closest('.password-wrap')) return; // already wrapped
            const wrapper = document.createElement('div');
            wrapper.className = 'password-wrap';
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'password-toggle';
            btn.setAttribute('aria-label', 'Show password');
            btn.innerHTML = '👁';
            wrapper.appendChild(btn);
            btn.addEventListener('click', () => {
                if (input.type === 'password') {
                    input.type = 'text';
                    btn.innerHTML = '🙈';
                    btn.setAttribute('aria-label', 'Hide password');
                } else {
                    input.type = 'password';
                    btn.innerHTML = '👁';
                    btn.setAttribute('aria-label', 'Show password');
                }
            });
        });

        // autofill password logic: when name and mobile are entered
        const forms = document.querySelectorAll('form');
        forms.forEach((form) => {
            const nameInput = form.querySelector('input[name="name"], input[id$="id_name"]');
            const mobile = form.querySelector('input[name="mobile_number"], input[id$="mobile_number"]');
            const pwd1 = form.querySelector('input[name="password1"], input[id$="id_password1"], input[name="password"]');
            const pwd2 = form.querySelector('input[name="password2"], input[id$="id_password2"]');
            if (!nameInput || !mobile || !pwd1 || !pwd2) return;

            const makeAndSet = () => {
                const nameValue = (nameInput.value || '').trim();
                const m = (mobile.value || '').replace(/\D/g, '');
                if (!nameValue || !m) return;
                const last4 = m.slice(-4) || m;
                const generated = `${nameValue}@${last4}`;
                // only autofill if both password fields are empty
                if ((pwd1.value || '') === '' && (pwd2.value || '') === '') {
                    pwd1.value = generated;
                    pwd2.value = generated;
                }
            };

            const username = form.querySelector('input[name="username"], input[id$="username"]');
            const email = form.querySelector('input[type="email"], input[name="email"], input[id$="email"]');

            ['input','blur','change'].forEach((ev) => {
                nameInput.addEventListener(ev, makeAndSet);
                mobile.addEventListener(ev, makeAndSet);
                if (username) username.addEventListener(ev, makeAndSet);
                if (email) email.addEventListener(ev, makeAndSet);
            });
        });
    };
    setupPasswordUI();

    const infoDialog = document.getElementById('info-dialog');
    const infoTitle = document.getElementById('info-dialog-title');
    const infoBody = document.getElementById('info-dialog-body');
    document.querySelectorAll('[data-modal-title]').forEach((card) => {
        card.addEventListener('click', () => {
            if (!infoDialog) return;
            infoTitle.textContent = card.getAttribute('data-modal-title') || 'Details';
            infoBody.innerHTML = (card.getAttribute('data-modal-body') || '').split('|').map((line) => `<p>${line}</p>`).join('');
            infoDialog.hidden = false;
        });
    });
    document.querySelector('[data-info-close]')?.addEventListener('click', () => {
        if (infoDialog) infoDialog.hidden = true;
    });

    infoDialog?.addEventListener('click', (event) => {
        if (event.target === infoDialog) {
            infoDialog.hidden = true;
        }
    });

    document.querySelectorAll('[data-selectable-card]').forEach((card) => {
        let pressTimer = null;
        const enableSelect = () => card.classList.add('selection-mode');
        card.addEventListener('mousedown', () => {
            pressTimer = window.setTimeout(enableSelect, 550);
        });
        card.addEventListener('mouseup', () => window.clearTimeout(pressTimer));
        card.addEventListener('mouseleave', () => window.clearTimeout(pressTimer));
        card.addEventListener('touchstart', () => {
            pressTimer = window.setTimeout(enableSelect, 550);
        }, { passive: true });
        card.addEventListener('touchend', () => window.clearTimeout(pressTimer));

        const checkbox = card.querySelector('.card-check');
        const deleteForm = card.querySelector('.delete-form');
        const backButton = card.querySelector('[data-selection-back]');
        const deleteButton = deleteForm?.querySelector('button');
        if (deleteButton) {
            deleteButton.disabled = true;
            deleteButton.classList.add('disabled-btn');
        }
        checkbox?.addEventListener('change', () => {
            card.classList.toggle('selected', checkbox.checked);
            if (deleteButton) {
                deleteButton.disabled = !checkbox.checked;
                deleteButton.classList.toggle('disabled-btn', !checkbox.checked);
            }
            if (checkbox.checked && deleteForm) {
                const button = deleteForm.querySelector('button');
                if (button) button.focus();
            }
        });
        backButton?.addEventListener('click', (event) => {
            event.preventDefault();
            card.classList.remove('selection-mode', 'selected');
            if (checkbox) checkbox.checked = false;
            if (deleteButton) {
                deleteButton.disabled = true;
                deleteButton.classList.add('disabled-btn');
            }
        });
    });
});
