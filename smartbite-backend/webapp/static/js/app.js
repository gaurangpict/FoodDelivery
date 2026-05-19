/* ============================================
   SmartBite — Client-side JavaScript
   ============================================ */

// ─── Toast Notifications ────────────────────

function showToast(message, type = '') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ─── Cart Badge Update ──────────────────────

function updateCartBadge(count) {
    const badge = document.getElementById('cart-badge');
    if (badge) {
        badge.textContent = count;
    }
}

// ─── Add to Cart (Menu Page) ────────────────

async function addToCart(itemId, restaurantId) {
    try {
        const resp = await fetch('/api/cart/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId, restaurant_id: restaurantId })
        });

        const data = await resp.json();

        if (resp.ok) {
            updateCartBadge(data.cart_count);
            showToast('✓ Added to cart', 'success');

            // Update button to show quantity control
            const menuItem = document.getElementById('item-' + itemId);
            if (menuItem) {
                const actionDiv = menuItem.querySelector('.menu-item-action');
                if (data.item_qty > 1) {
                    // Update existing qty display
                    const qtyEl = actionDiv.querySelector('.qty-display');
                    if (qtyEl) qtyEl.textContent = data.item_qty;
                } else {
                    // Replace ADD button with qty control
                    actionDiv.innerHTML = `
                        <div class="qty-control">
                            <button onclick="menuUpdateQty('${itemId}', '${restaurantId}', 'decrement')">−</button>
                            <span class="qty-display">${data.item_qty}</span>
                            <button onclick="menuUpdateQty('${itemId}', '${restaurantId}', 'increment')">+</button>
                        </div>
                    `;
                }
            }
        } else {
            showToast('Failed to add item');
        }
    } catch (err) {
        showToast('Network error');
    }
}

// ─── Menu Page Qty Control ──────────────────

async function menuUpdateQty(itemId, restaurantId, action) {
    try {
        const resp = await fetch('/api/cart/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId, action: action })
        });

        const data = await resp.json();

        if (resp.ok) {
            updateCartBadge(data.cart_count);

            const menuItem = document.getElementById('item-' + itemId);
            if (menuItem) {
                const actionDiv = menuItem.querySelector('.menu-item-action');
                if (data.item_qty <= 0) {
                    // Restore ADD button
                    actionDiv.innerHTML = `
                        <button class="add-btn"
                                onclick="addToCart('${itemId}', '${restaurantId}')">
                            ADD
                        </button>
                    `;
                } else {
                    const qtyEl = actionDiv.querySelector('.qty-display');
                    if (qtyEl) qtyEl.textContent = data.item_qty;
                }
            }
        }
    } catch (err) {
        showToast('Network error');
    }
}

// ─── Cart Page: Update Quantity ─────────────

async function updateCart(itemId, action) {
    try {
        const resp = await fetch('/api/cart/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId, action: action })
        });

        const data = await resp.json();

        if (resp.ok) {
            updateCartBadge(data.cart_count);

            if (data.item_qty <= 0) {
                // Remove item row
                const row = document.getElementById('cart-item-' + itemId);
                if (row) row.remove();

                // If cart is now empty, reload
                if (data.cart_count === 0) {
                    window.location.reload();
                    return;
                }
            } else {
                // Update quantity and total display
                const qtyEl = document.getElementById('qty-' + itemId);
                const totalEl = document.getElementById('total-' + itemId);
                if (qtyEl) qtyEl.textContent = data.item_qty;
                if (totalEl) totalEl.textContent = '₹' + data.item_total;
            }

            // Update subtotal display
            const itemTotalEl = document.getElementById('bill-item-total');
            if (itemTotalEl) itemTotalEl.textContent = '₹' + data.subtotal;

            // Recalculate bill
            recalculate();
        }
    } catch (err) {
        showToast('Network error');
    }
}

// ─── Cart Page: Remove Item ─────────────────

async function removeFromCart(itemId) {
    try {
        const resp = await fetch('/api/cart/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId })
        });

        const data = await resp.json();

        if (resp.ok) {
            updateCartBadge(data.cart_count);

            // Remove item row
            const row = document.getElementById('cart-item-' + itemId);
            if (row) row.remove();

            if (data.cart_count === 0) {
                window.location.reload();
                return;
            }

            const itemTotalEl = document.getElementById('bill-item-total');
            if (itemTotalEl) itemTotalEl.textContent = '₹' + data.subtotal;

            recalculate();
            showToast('Item removed');
        }
    } catch (err) {
        showToast('Network error');
    }
}

// ─── Delivery Type Selection ────────────────

function selectDelivery(type) {
    document.querySelectorAll('.delivery-option').forEach(el => el.classList.remove('selected'));
    const opt = document.getElementById('opt-' + type);
    if (opt) opt.classList.add('selected');

    // Update hidden form field
    const formField = document.getElementById('form-delivery-type');
    if (formField) formField.value = type;

    recalculate();
}

// ─── Payment Method Selection ───────────────

function selectPayment(el, method) {
    document.querySelectorAll('.payment-option').forEach(opt => opt.classList.remove('selected'));
    el.classList.add('selected');

    const formField = document.getElementById('form-payment');
    if (formField) formField.value = method;
}

// ─── Live Bill Recalculation ────────────────────

let recalcTimer = null;

function recalculate() {
    // Debounce
    if (recalcTimer) clearTimeout(recalcTimer);
    recalcTimer = setTimeout(doRecalculate, 200);
}

async function doRecalculate() {
    const distanceEl = document.getElementById('distance-input');
    const promoEl = document.getElementById('promo-input');

    if (!distanceEl) return; // not on cart page

    const deliveryType = document.querySelector('input[name="delivery_type"]:checked');

    const payload = {
        distance: parseFloat(distanceEl.value) || 5,
        promo_discount: parseFloat(promoEl.value) || 0,
        delivery_type: deliveryType ? deliveryType.value : 'standard'
    };

    // Sync hidden form fields
    const formDist = document.getElementById('form-distance');
    const formPromo = document.getElementById('form-promo');
    if (formDist) formDist.value = payload.distance;
    if (formPromo) formPromo.value = payload.promo_discount;

    try {
        const resp = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) return;

        const bill = await resp.json();

        // Update bill display
        document.getElementById('bill-item-total').textContent = '₹' + bill.item_total.toFixed(2);
        document.getElementById('bill-delivery-fee').textContent = '₹' + bill.delivery_fee.toFixed(2);
        document.getElementById('bill-food-gst').textContent = '₹' + bill.food_gst.toFixed(2);
        document.getElementById('bill-service-gst').textContent = '₹' + bill.service_gst.toFixed(2);
        document.getElementById('bill-final-total').textContent = '₹' + bill.final_total.toFixed(2);

        // Discount
        const discountRow = document.getElementById('bill-discount-row');
        if (bill.total_discount > 0) {
            discountRow.style.display = 'flex';
            document.getElementById('bill-discount').textContent = '-₹' + bill.total_discount.toFixed(2);
        } else {
            discountRow.style.display = 'none';
        }

        // Batch info
        const batchInfo = document.getElementById('batch-info');
        if (bill.is_batched) {
            batchInfo.style.display = 'flex';
        } else {
            batchInfo.style.display = 'none';
        }

        // Engine metrics
        document.getElementById('engine-demand').textContent = bill.demand_level.toUpperCase();
        document.getElementById('engine-score').textContent = bill.smart_score;

    } catch (err) {
        // Silently fail on network errors during recalculation
    }
}
