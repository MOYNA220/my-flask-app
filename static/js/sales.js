document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const itemSearch = document.getElementById('item-search');
    const itemsTable = document.getElementById('items-table');
    const cartTable = document.getElementById('cart-items');
    const paymentMethod = document.getElementById('payment-method');
    const cashSection = document.getElementById('cash-section');
    const splitSection = document.getElementById('split-section');
    const receivedAmount = document.getElementById('received-amount');
    const cashAmount = document.getElementById('cash-amount');
    const onlineAmount = document.getElementById('online-amount');
    const dueAmount = document.getElementById('due-amount');
    const refundAmount = document.getElementById('refund-amount');
    const completeSaleBtn = document.getElementById('complete-sale');
    const updateSaleBtn = document.getElementById('update-sale');
    const cancelSaleBtn = document.getElementById('cancel-sale');
    const customerSelect = document.getElementById('customer-select');

    // Global Cart
    window.cart = [];
    let itemsToDelete = [];

    // Initialize cart if editing
    if (window.saleItems) {
        window.cart = window.saleItems.map(item => ({
            id: item.item_id,
            item_id: item.item_id,
            name: item.name || `Item #${item.item_id}`,
            quantity: item.quantity,
            unit: item.unit,
            price: item.sale_price,
            sale_price: item.sale_price,
            purchase_price: item.purchase_price,
            stock: item.stock || 0,
            sale_item_id: item.sale_item_id || item.id || null
        }));
        updateCartDisplay();
    }

    // 1. Item Search
    if (itemSearch) {
        itemSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = itemsTable.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const itemName = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
                row.style.display = itemName.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // 2. Add to Cart
    if (itemsTable) {
        itemsTable.addEventListener('click', function(e) {
            if (e.target.classList.contains('add-to-cart')) {
                const button = e.target;
                const row = button.closest('tr');
                const quantityInput = row.querySelector('.item-quantity');
                
                const item = {
                    id: parseInt(button.dataset.itemId),
                    item_id: parseInt(button.dataset.itemId),
                    name: button.dataset.itemName,
                    quantity: parseFloat(quantityInput.value) || 1,
                    unit: button.dataset.itemUnit,
                    price: parseFloat(button.dataset.itemPrice),
                    sale_price: parseFloat(button.dataset.itemPrice),
                    purchase_price: parseFloat(button.dataset.itemPurchasePrice),
                    stock: parseFloat(row.querySelector('td:nth-child(3)').textContent)
                };

                // Validate quantity
                if (item.quantity <= 0) {
                    alert('Quantity must be greater than 0');
                    return;
                }
                if (item.quantity > item.stock) {
                    alert(`Only ${item.stock} available in stock`);
                    return;
                }
                if (isNaN(item.purchase_price)) {
                    alert('This item is missing purchase price information');
                    return;
                }

                // Check existing item
                const existingIndex = window.cart.findIndex(i => i.id === item.id);
                if (existingIndex >= 0) {
                    window.cart[existingIndex].quantity += item.quantity;
                } else {
                    window.cart.push(item);
                }

                // Reset quantity input
                quantityInput.value = 1;
                
                updateCartDisplay();
            }
        });
    }

    // 3. Remove from Cart
    if (cartTable) {
        cartTable.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-item')) {
                const itemId = parseInt(e.target.dataset.itemId);
                const saleItemId = e.target.dataset.saleItemId ? parseInt(e.target.dataset.saleItemId) : null;
                
                window.cart = window.cart.filter(item => item.id !== itemId);
                
                if (saleItemId) {
                    itemsToDelete.push(saleItemId);
                }
                
                updateCartDisplay();
            }
        });
    }

    // 4. Payment Method Toggle
    if (paymentMethod) {
        paymentMethod.addEventListener('change', function() {
            if (this.value === 'Split') {
                cashSection.style.display = 'none';
                splitSection.style.display = 'block';
            } else {
                cashSection.style.display = 'block';
                splitSection.style.display = 'none';
            }
            calculatePayment();
        });
    }

    // 5. Payment Calculation
    [receivedAmount, cashAmount, onlineAmount].forEach(input => {
        if (input) {
            input.addEventListener('input', calculatePayment);
        }
    });

    // 6. Complete Sale
    if (completeSaleBtn) {
        completeSaleBtn.addEventListener('click', function() {
            processSale('/new_sale');
        });
    }

    // 7. Update Sale
    if (updateSaleBtn) {
        updateSaleBtn.addEventListener('click', function() {
            processSale(`/sales/${window.saleId}/update`);
        });
    }

    // 8. Cancel Sale
    if (cancelSaleBtn) {
        cancelSaleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (window.cart.length === 0 || confirm('Are you sure you want to cancel? All changes will be lost.')) {
                if (window.saleId) {
                    window.location.href = `/sales/${window.saleId}`;
                } else {
                    window.location.href = '/sales';
                }
            }
        });
    }

    // 9. Delete Sale
    const deleteSaleBtn = document.getElementById('delete-sale');
    if (deleteSaleBtn) {
        deleteSaleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Are you sure you want to delete this sale? This action cannot be undone.')) {
                fetch(`/sales/${window.saleId}/delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => {
                    if (!response.ok) return response.json().then(err => { throw err; });
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        alert('Sale deleted successfully!');
                        window.location.href = '/sales'; // Redirect back to sales list
                    } else {
                        alert('Error: ' + (data.message || 'Failed to delete sale'));
                    }
                })
                .catch(error => {
                    console.error('Delete Error:', error);
                    alert('Failed to delete sale: ' + (error.message || 'Check console for details'));
                });
            }
        });
    }

    // ---------------- Helper Functions ----------------
    function updateCartDisplay() {
        const tbody = cartTable.querySelector('tbody');
        tbody.innerHTML = '';

        let subtotal = 0;

        window.cart.forEach(item => {
            const row = document.createElement('tr');
            const itemTotal = item.price * item.quantity;
            subtotal += itemTotal;

            row.innerHTML = `
                <td>${item.name}</td>
                <td>
                    <input type="number" class="form-control item-quantity-update" 
                           value="${item.quantity}" min="0.01" step="0.01" 
                           data-item-id="${item.id}" style="width: 80px;">
                </td>
                <td>${item.unit}</td>
                <td>₹${item.price.toFixed(2)}</td>
                <td>₹${itemTotal.toFixed(2)}</td>
                <td>
                    <button class="btn btn-danger btn-sm remove-item" 
                            data-item-id="${item.id}" 
                            ${item.sale_item_id ? `data-sale-item-id="${item.sale_item_id}"` : ''}>
                        ❌
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });

        // Attach quantity change events
        document.querySelectorAll('.item-quantity-update').forEach(input => {
            input.addEventListener('change', function() {
                const itemId = parseInt(this.dataset.itemId);
                const newQuantity = parseFloat(this.value);
                const item = window.cart.find(i => i.id === itemId);
                
                if (item) {
                    if (newQuantity <= 0) {
                        alert('Quantity must be greater than 0');
                        this.value = item.quantity;
                        return;
                    }
                    if (newQuantity > item.stock + item.quantity) {
                        alert(`Only ${item.stock + item.quantity} available in stock`);
                        this.value = item.quantity;
                        return;
                    }
                    item.quantity = newQuantity;
                    updateCartDisplay();
                }
            });
        });

        document.getElementById('subtotal').textContent = `₹${subtotal.toFixed(2)}`;
        calculatePayment();
    }

    function calculatePayment() {
        const subtotal = window.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
        const method = paymentMethod.value;
        let received = 0;
        let cash = 0;
        let online = 0;

        if (method === 'Split') {
            cash = parseFloat(cashAmount.value) || 0;
            online = parseFloat(onlineAmount.value) || 0;
            received = cash + online;
        } else {
            received = parseFloat(receivedAmount.value) || 0;
            if (method === 'Cash') cash = received;
            if (method === 'Online') online = received;
        }

        const due = Math.max(0, subtotal - received);
        const refund = Math.max(0, received - subtotal);

        dueAmount.value = `₹${due.toFixed(2)}`;
        refundAmount.value = `₹${refund.toFixed(2)}`;
        document.getElementById('subtotal').textContent = `₹${subtotal.toFixed(2)}`;
    }

    function processSale(url) {
        if (window.cart.length === 0) {
            alert('Please add items to cart');
            return;
        }

        const itemsMissingPurchasePrice = window.cart.filter(item => 
            typeof item.purchase_price === 'undefined' || isNaN(item.purchase_price)
        );
        if (itemsMissingPurchasePrice.length > 0) {
            alert('Some items are missing purchase price information');
            return;
        }

        const customerId = customerSelect.value;
        const paymentMethodValue = paymentMethod.value;
        let received = 0;
        let cash = 0;
        let online = 0;

        if (paymentMethodValue === 'Split') {
            cash = parseFloat(cashAmount.value) || 0;
            online = parseFloat(onlineAmount.value) || 0;
            received = cash + online;
        } else {
            received = parseFloat(receivedAmount.value) || 0;
            if (paymentMethodValue === 'Cash') cash = received;
            if (paymentMethodValue === 'Online') online = received;
        }

        const subtotal = window.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const due = subtotal - received;

        if (due > 0 && !customerId) {
            alert('Please select a customer for credit sale');
            return;
        }

        const saleData = {
            customer_id: customerId || null,
            payment_method: paymentMethodValue,
            received_amount: received,
            cash_amount: cash,
            online_amount: online,
            items: window.cart.map(item => ({
                id: item.sale_item_id || null,
                item_id: item.id,
                name: item.name,
                quantity: item.quantity,
                unit: item.unit,
                price: item.price,
                sale_price: item.sale_price,
                purchase_price: item.purchase_price
            })),
            items_to_delete: itemsToDelete
        };

        fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(saleData)
        })
        .then(response => {
            if (!response.ok) return response.json().then(err => { throw err; });
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const action = url.includes('update') ? 'updated' : 'completed';
                alert(`Sale ${action} successfully! Bill No: ${data.bill_number}`);
                window.location.href = `/sales/${data.sale_id}`;
            } else {
                alert('Error: ' + (data.message || 'Unknown error occurred'));
            }
        })
        .catch(error => {
            console.error('Sale Error:', {error, saleData, cart: window.cart});
            alert('Failed to process sale: ' + (error.message || 'Check console for details'));
        });
    }

    // Initialize
    calculatePayment();

    // ===============================
    // 10. New Customer Modal Handling
    // ===============================
    const newCustomerForm = document.getElementById("new-customer-form");
    if (newCustomerForm) {
        newCustomerForm.addEventListener("submit", async function(e) {
            e.preventDefault();

            const name = document.getElementById("customer-name").value;
            const mobile = document.getElementById("customer-mobile").value;
            const address = document.getElementById("customer-address").value;

            try {
                const response = await fetch("/api/customers/add", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, mobile, address })
                });

                const data = await response.json();
                if (data.success) {
                    // Update dropdown
                    const option = document.createElement("option");
                    option.value = data.customer.id;
                    option.textContent = `${data.customer.name} (${data.customer.mobile || ''})`;
                    customerSelect.appendChild(option);
                    customerSelect.value = data.customer.id;

                    // Close modal
                    const modalEl = document.getElementById("newCustomerModal");
                    bootstrap.Modal.getInstance(modalEl).hide();

                    // Reset form
                    newCustomerForm.reset();
                } else {
                    alert(data.message || "Error adding customer!");
                }
            } catch (err) {
                console.error(err);
                alert("Server error while adding customer.");
            }
        });
    }

}); //
