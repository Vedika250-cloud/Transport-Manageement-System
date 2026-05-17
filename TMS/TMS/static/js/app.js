document.addEventListener('DOMContentLoaded', () => {
    // Animate table rows sequentially
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(10px)';
        row.style.animation = `fadeIn 0.3s ease forwards ${index * 0.05}s`;
    });

    // Global Confirmation Handler for Links/Buttons
    document.addEventListener('click', (e) => {
        const confirmBtn = e.target.closest('[data-confirm]');
        if (confirmBtn) {
            e.preventDefault();
            const message = confirmBtn.getAttribute('data-confirm');
            const url = confirmBtn.getAttribute('href');
            const isDanger = confirmBtn.classList.contains('delete') || confirmBtn.classList.contains('danger');
            
            showConfirm('Confirm Action', message, () => {
                if (url && url !== '#') {
                    window.location.href = url;
                } else if (confirmBtn.tagName.toLowerCase() === 'button' && confirmBtn.form) {
                    confirmBtn.form.submit();
                }
            }, isDanger);
        }
    });

    // Add visual status badge classes & fix alignment
    document.querySelectorAll('td').forEach(cell => {
        let statusClass = Array.from(cell.classList).find(c => c.startsWith('status-') && c !== 'status-badge');
        const text = cell.innerText.trim().toLowerCase();
        
        // Auto-detect status if not set server-side
        if (!statusClass) {
            if (['active', 'completed', 'paid', 'delivered', 'available'].includes(text)) {
                statusClass = 'status-active';
            } else if (['pending', 'inactive', 'in transit', 'unpaid', 'processing', 'booked'].includes(text)) {
                statusClass = 'status-pending';
            } else if (['in_use'].includes(text)) {
                statusClass = 'status-in_use';
            } else if (['maintenance'].includes(text)) {
                statusClass = 'status-maintenance';
            }
        }

        // If a status applies and is not yet wrapped in a span
        if (statusClass && cell.children.length === 0) {
            const originalText = cell.innerText.trim();
            cell.innerText = '';
            
            const badge = document.createElement('span');
            badge.className = statusClass;
            badge.innerText = originalText;
            
            cell.appendChild(badge);
            
            // Remove the badge class from the td to restore vertical tracking
            cell.classList.remove(statusClass);
            cell.classList.add('status');
            cell.style.verticalAlign = 'middle';
            cell.style.textAlign = 'center';
        }
    });

    // Global Custom Select Dropdowns
    const selects = document.querySelectorAll('select:not(.no-custom)');
    selects.forEach(select => {
        // Hide original native select
        select.style.display = 'none';

        // Create the custom wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper';
        
        // Create custom trigger button
        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        
        let selectedOption = select.options[select.selectedIndex];
        let selectedText = selectedOption ? selectedOption.text : 'Select...';
        
        trigger.innerHTML = `<span>${selectedText}</span><svg class="arrow" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"></polyline></svg>`;
        
        // Create custom options dropdown list
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'custom-options';
        
        // Append to body to completely avoid overflow clipping from tables/cards!
        document.body.appendChild(optionsContainer);

        // Add search input if searchable
        if (select.dataset.searchable === 'true') {
            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.className = 'custom-select-search';
            searchInput.placeholder = 'Search...';
            
            searchInput.addEventListener('click', (e) => e.stopPropagation());
            searchInput.addEventListener('keyup', (e) => {
                const filter = e.target.value.toLowerCase();
                const opts = optionsContainer.querySelectorAll('.custom-option');
                opts.forEach(opt => {
                    if (opt.textContent.toLowerCase().includes(filter)) {
                        opt.classList.remove('hidden');
                    } else {
                        opt.classList.add('hidden');
                    }
                });
            });
            optionsContainer.appendChild(searchInput);
        }

        // Populate options based on native select options
        Array.from(select.options).forEach((option) => {
            const customOption = document.createElement('div');
            customOption.className = 'custom-option';
            if(option.selected) customOption.classList.add('selected');
            
            customOption.textContent = option.text;
            customOption.dataset.value = option.value;
            
            // When custom option is clicked
            customOption.addEventListener('click', (e) => {
                e.stopPropagation();
                // Assign value to original select so form submission works properly
                if (select.value !== option.value) {
                    select.value = option.value;
                    // Trigger native change event so inline onchange and listeners work
                    select.dispatchEvent(new Event('change'));
                }
                
                // Update text
                trigger.querySelector('span').textContent = option.text;
                
                // Refresh selection styles
                optionsContainer.querySelectorAll('.custom-option').forEach(opt => opt.classList.remove('selected'));
                customOption.classList.add('selected');
                
                // Reset search if exists
                const search = optionsContainer.querySelector('.custom-select-search');
                if (search) {
                    search.value = '';
                    optionsContainer.querySelectorAll('.custom-option').forEach(opt => opt.classList.remove('hidden'));
                }
                
                // Close wrapper
                wrapper.classList.remove('open');
                optionsContainer.classList.remove('open');
            });
            optionsContainer.appendChild(customOption);
        });

        // Function to update position
        const updatePosition = () => {
            if (!optionsContainer.classList.contains('open')) return;
            const rect = trigger.getBoundingClientRect();
            const dropdownHeight = 250; // Max height approx
            const spaceBelow = window.innerHeight - rect.bottom;
            
            optionsContainer.style.width = rect.width + 'px';
            optionsContainer.style.left = rect.left + window.scrollX + 'px';

            if (spaceBelow < dropdownHeight && rect.top > dropdownHeight) {
                // Open upwards
                optionsContainer.style.top = 'auto';
                optionsContainer.style.bottom = (window.innerHeight - rect.top - window.scrollY + 6) + 'px';
            } else {
                // Open downwards
                optionsContainer.style.top = (rect.bottom + window.scrollY + 6) + 'px';
                optionsContainer.style.bottom = 'auto';
            }
        };

        // Toggle open/close logic
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            // Close other open wrappers
            document.querySelectorAll('.custom-select-wrapper').forEach(w => w.classList.remove('open'));
            document.querySelectorAll('.custom-options').forEach(o => o.classList.remove('open'));
            
            wrapper.classList.toggle('open');
            
            if (wrapper.classList.contains('open')) {
                optionsContainer.classList.add('open');
                updatePosition();

                // Force layout reflow so animation works properly with new transform origin
                void optionsContainer.offsetWidth;
                optionsContainer.style.transform = 'translateY(0)';

                const search = optionsContainer.querySelector('.custom-select-search');
                if (search) setTimeout(() => search.focus(), 100);
            }
        });

        window.addEventListener('scroll', updatePosition, true);
        window.addEventListener('resize', updatePosition);

        wrapper.appendChild(trigger);
        // We append the optionsContainer to document.body initially so it's not inside wrapper anymore
        select.parentNode.insertBefore(wrapper, select.nextSibling);
        
        // Listen for external changes to the native select (e.g. resets)
        select.addEventListener('change', () => {
            const newSelected = select.options[select.selectedIndex];
            if (newSelected) {
                trigger.querySelector('span').textContent = newSelected.text;
                optionsContainer.querySelectorAll('.custom-option').forEach(opt => {
                    opt.classList.toggle('selected', opt.dataset.value === newSelected.value);
                });
            }
        });
    });

    // Close all when clicking outside
    document.addEventListener('click', () => {
        document.querySelectorAll('.custom-select-wrapper').forEach(w => w.classList.remove('open'));
        document.querySelectorAll('.custom-options').forEach(o => o.classList.remove('open'));
    });

    // Live Table Search Filter
    const searchInput = document.getElementById('tableSearch');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('.data-table tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(filter)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

/* ========================
   Global Modals & Toasts
   ======================== */

window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('open');
        // Focus trap & accessibility
        const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
        const firstFocusableElement = modal.querySelectorAll(focusableElements)[0];
        if (firstFocusableElement) {
            setTimeout(() => firstFocusableElement.focus(), 100);
        }
    }
}

window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('open');
    }
}

// Close modals on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal-overlay.open');
        openModals.forEach(modal => closeModal(modal.id));
    }
});

// Close modals on clicking backdrop
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal(e.target.id);
    }
});

window.showConfirm = function(title, message, onConfirmCallback, isDanger = true) {
    document.getElementById('globalConfirmTitle').innerText = title;
    document.getElementById('globalConfirmMessage').innerText = message;
    
    const confirmBtn = document.getElementById('globalConfirmBtn');
    
    // Style button based on danger level
    if (isDanger) {
        confirmBtn.className = 'btn btn-danger';
    } else {
        confirmBtn.className = 'btn btn-primary';
    }
    
    // Remove old event listeners by cloning
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    newConfirmBtn.addEventListener('click', () => {
        closeModal('globalConfirmModal');
        if(onConfirmCallback) onConfirmCallback();
    });
    
    openModal('globalConfirmModal');
}

window.showAlert = function(title, message, type = 'info') {
    document.getElementById('globalAlertTitle').innerText = title;
    document.getElementById('globalAlertMessage').innerText = message;
    
    const iconContainer = document.getElementById('globalAlertIcon');
    iconContainer.className = `modal-icon-container ${type}`;
    
    let iconName = 'info';
    if(type === 'danger') iconName = 'alert-triangle';
    if(type === 'warning') iconName = 'alert-circle';
    if(type === 'success') iconName = 'check-circle';
    
    iconContainer.innerHTML = `<i data-lucide="${iconName}"></i>`;
    if(window.lucide) lucide.createIcons();
    
    openModal('globalAlertModal');
}

window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconName = 'info';
    if(type === 'error' || type === 'danger') iconName = 'alert-circle';
    if(type === 'warning') iconName = 'alert-triangle';
    if(type === 'success') iconName = 'check-circle';
    
    toast.innerHTML = `
        <i data-lucide="${iconName}" class="toast-icon"></i>
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.classList.add('fade-out'); setTimeout(() => this.parentElement.remove(), 400)"><i data-lucide="x"></i></button>
        <div class="toast-progress"></div>
    `;
    
    container.appendChild(toast);
    if(window.lucide) lucide.createIcons();
    
    // Auto-dismiss after 4 seconds matching the progress animation
    setTimeout(() => {
        if(toast.parentElement) {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 400);
        }
    }, 4000);
}
