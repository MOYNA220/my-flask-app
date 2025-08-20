from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import os
import json
from functools import wraps
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stock_sale.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Add this line

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.Date, default=date.today())
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15))
    address = db.Column(db.String(200))
    aadhar = db.Column(db.String(20))
    date_added = db.Column(db.Date, default=date.today())
    photo_path = db.Column(db.String(200))


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15))
    address = db.Column(db.String(200))
    gstin = db.Column(db.String(20))
    date_added = db.Column(db.Date, default=date.today())
    balance = db.Column(db.Float, default=0.0)
    
    # Relationships
    items = db.relationship('Item', backref='supplier', lazy=True)
    transactions = db.relationship('SupplierTransaction', 
                                 backref='supplier', 
                                 cascade='all, delete-orphan',
                                 lazy='dynamic')  # Changed to dynamic for better query control

class SupplierTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today())
    bill_no = db.Column(db.String(50))
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'purchase' or 'payment'
    created_at = db.Column(db.DateTime, default=datetime.now())
    
    def __repr__(self):
        return f"<SupplierTransaction {self.id} - {self.transaction_type} - {self.amount}>"

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(20), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    sale_date = db.Column(db.Date, nullable=False)
    sale_time = db.Column(db.String(10), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    received_amount = db.Column(db.Float, nullable=False)
    due_amount = db.Column(db.Float, nullable=False)
    total_profit = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20))
    cash_amount = db.Column(db.Float, default=0.0)
    online_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now())
    
    # Relationships
    customer = db.relationship('Customer', backref='sales')
    items = db.relationship(
        'SaleItem',
        back_populates='sale',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)
    
    # Relationships
    sale = db.relationship('Sale', back_populates='items')
    item = db.relationship('Item', backref='sale_items')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now())

# Create tables
with app.app_context():
    db.create_all()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Create Admin User ---
def create_admin_user():
    with app.app_context():
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")

# Initialize database and admin user
with app.app_context():
    db.create_all()  # Create tables
    create_admin_user()  # Add admin user

# --- Your Routes Here ---
@app.route('/')
def home():
    return "Hello World!"


@app.route('/dashboard')
@login_required
def dashboard():
    # Today's summary
    today = date.today()
    
    # Total sales today
    sales_today = Sale.query.filter_by(sale_date=today).all()
    total_sales = sum(sale.total_amount for sale in sales_today)
    total_received = sum(sale.received_amount for sale in sales_today)
    total_due = sum(sale.due_amount for sale in sales_today)
    total_profit = sum(sale.total_profit for sale in sales_today)
    
    # New customers today
    new_customers = Customer.query.filter_by(date_added=today).count()
    
    # Low stock items
    low_stock_items = Item.query.filter(Item.quantity < 2).order_by(Item.quantity).all()
    
    # Recent sales
    recent_sales = Sale.query.order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(10).all()
    
    return render_template('dashboard.html', 
                         total_sales=total_sales,
                         total_received=total_received,
                         total_due=total_due,
                         total_profit=total_profit,
                         new_customers=new_customers,
                         low_stock_items=low_stock_items,
                         recent_sales=recent_sales)

# Items Management
@app.route('/items')
@login_required
def items():
    search_term = request.args.get('search', '')
    
    if search_term:
        items = Item.query.filter(Item.name.ilike(f'%{search_term}%')).order_by(Item.name).all()
    else:
        items = Item.query.order_by(Item.id).all()
    
    return render_template('items.html', items=items, search_term=search_term)

@app.route('/items/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        quantity = float(request.form['quantity'])
        unit = request.form['unit']
        purchase_price = float(request.form['purchase_price'])
        sale_price = float(request.form['sale_price'])
        
        if not name:
            flash('Item name is required', 'danger')
            return redirect(url_for('add_item'))
        
        try:
            new_item = Item(
                name=name,
                quantity=quantity,
                unit=unit,
                purchase_price=purchase_price,
                sale_price=sale_price,
                date_added=date.today()
            )
            db.session.add(new_item)
            db.session.commit()
            
            flash('Item added successfully', 'success')
            return redirect(url_for('items'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding item: {str(e)}', 'danger')
    
    return render_template('add_item.html')

@app.route('/items/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    item = Item.query.get_or_404(id)
    
    if request.method == 'POST':
        item.name = request.form['name']
        item.quantity = float(request.form['quantity'])
        item.unit = request.form['unit']
        item.purchase_price = float(request.form['purchase_price'])
        item.sale_price = float(request.form['sale_price'])
        
        try:
            db.session.commit()
            flash('Item updated successfully', 'success')
            return redirect(url_for('items'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'danger')
    
    return render_template('edit_item.html', item=item)

@app.route('/items/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    item = Item.query.get_or_404(id)
    
    # Check if item is in any sales
    sale_items = SaleItem.query.filter_by(item_id=id).count()
    if sale_items > 0:
        flash('Cannot delete item as it exists in sales records', 'danger')
        return redirect(url_for('items'))
    
    try:
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'danger')
    
    return redirect(url_for('items'))

# Sales Management
@app.route('/sales')
@login_required
def sales():
    search_term = request.args.get('search', '')
    
    if search_term:
        sales = Sale.query.filter(Sale.bill_number.ilike(f'%{search_term}%')).order_by(Sale.sale_date.desc()).all()
    else:
        sales = Sale.query.order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(50).all()
    
    return render_template('sales.html', sales=sales, search_term=search_term)

@app.route('/new_sale', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        try:
            # Get JSON data from request
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data received'}), 400

            # Extract data from JSON
            customer_id = data.get('customer_id')
            payment_method = data.get('payment_method')
            if not payment_method:
                return jsonify({'success': False, 'message': 'Payment method is required'}), 400

            received_amount = float(data.get('received_amount', 0))
            cash_amount = float(data.get('cash_amount', 0))
            online_amount = float(data.get('online_amount', 0))
            items = data.get('items', [])
            
            if not items:
                return jsonify({'success': False, 'message': 'Cart is empty'}), 400
            
            # Calculate totals
            total_amount = sum(item['sale_price'] * item['quantity'] for item in items)
            total_profit = sum((item['sale_price'] - item['purchase_price']) * item['quantity'] for item in items)
            due_amount = max(0, total_amount - received_amount)
            
            # Generate bill number
            today = date.today().strftime("%Y%m%d")
            count = Sale.query.filter(Sale.bill_number.like(f"{today}%")).count() + 1
            bill_number = f"{today}-{count:04d}"
            
            # Create sale record
            new_sale = Sale(
                bill_number=bill_number,
                customer_id=customer_id if customer_id else None,
                sale_date=date.today(),
                sale_time=datetime.now().strftime("%H:%M:%S"),
                total_amount=total_amount,
                received_amount=received_amount,
                due_amount=due_amount,
                total_profit=total_profit,
                payment_method=payment_method,
                cash_amount=cash_amount if payment_method in ['Cash', 'Split'] else 0,
                online_amount=online_amount if payment_method in ['Online', 'Split'] else 0
            )
            
            db.session.add(new_sale)
            db.session.flush()  # Get the sale ID
            
            # Add sale items and update stock
            for item_data in items:
                # Add sale item
                sale_item = SaleItem(
                    sale_id=new_sale.id,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity'],
                    unit=item_data['unit'],
                    purchase_price=item_data['purchase_price'],
                    sale_price=item_data['sale_price'],
                    profit=(item_data['sale_price'] - item_data['purchase_price']) * item_data['quantity']
                )
                db.session.add(sale_item)
                
                # Update stock
                db_item = Item.query.get(item_data['item_id'])
                if not db_item:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': f'Item with ID {item_data["item_id"]} not found'}), 400
                
                if db_item.quantity < item_data['quantity']:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': f'Not enough stock for {db_item.name}'}), 400
                
                db_item.quantity -= item_data['quantity']
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Sale completed successfully',
                'bill_number': bill_number,
                'sale_id': new_sale.id
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Sale failed: {str(e)}', exc_info=True)
            return jsonify({
                'success': False,
                'message': f'Failed to complete sale: {str(e)}'
            }), 500

    # GET request - show form
    items = Item.query.filter(Item.quantity > 0).order_by(Item.name).all()
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('new_sale.html', 
                         items=items, 
                         customers=customers,
                         cart=[])

@app.route('/sales/<int:id>')
@login_required
def view_sale(id):
    # Debugging: Print the sale items to console
    sale = Sale.query.options(
        db.joinedload(Sale.customer),
        db.joinedload(Sale.items).joinedload(SaleItem.item)
    ).get_or_404(id)
    
    print("DEBUG - Sale Items:")  # Add this for debugging
    for item in sale.items:
        print(f"Item ID: {item.item_id}, Name: {item.item.name if item.item else 'None'}")
    
    return render_template('view_sale.html', sale=sale)

@app.route('/sales/<int:id>/edit')
@login_required
def edit_sale(id):
    sale = Sale.query.options(
        db.joinedload(Sale.customer),
        db.joinedload(Sale.items).joinedload(SaleItem.item)
    ).get_or_404(id)
    
    items = Item.query.filter(Item.quantity > 0).order_by(Item.name).all()
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template('edit_sale.html', 
                         sale=sale,
                         items=items, 
                         customers=customers,
                         max=max)  # Pass Python's built-in max function to the template

@app.route('/sales/<int:id>/update', methods=['POST'])
@login_required
def update_sale(id):
    sale = Sale.query.get_or_404(id)
    
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400

        # Extract data from JSON
        customer_id = data.get('customer_id')
        payment_method = data.get('payment_method')
        if not payment_method:
            return jsonify({'success': False, 'message': 'Payment method is required'}), 400

        received_amount = float(data.get('received_amount', 0))
        cash_amount = float(data.get('cash_amount', 0))
        online_amount = float(data.get('online_amount', 0))
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        
        # Calculate totals
        total_amount = sum(item['sale_price'] * item['quantity'] for item in items)
        total_profit = sum((item['sale_price'] - item['purchase_price']) * item['quantity'] for item in items)
        due_amount = max(0, total_amount - received_amount)
        
        # Update sale record
        sale.customer_id = customer_id if customer_id else None
        sale.payment_method = payment_method
        sale.total_amount = total_amount
        sale.received_amount = received_amount
        sale.due_amount = due_amount
        sale.total_profit = total_profit
        sale.cash_amount = cash_amount if payment_method in ['Cash', 'Split'] else 0
        sale.online_amount = online_amount if payment_method in ['Online', 'Split'] else 0
        
        # Track which items to keep
        existing_item_ids = set()
        
        # Process each item in the updated sale
        for item_data in items:
            if 'id' in item_data and item_data['id']:  # Existing sale item
                sale_item = SaleItem.query.get(item_data['id'])
                if not sale_item:
                    continue
                
                # Update existing sale item
                original_quantity = sale_item.quantity
                sale_item.quantity = item_data['quantity']
                sale_item.unit = item_data['unit']
                sale_item.sale_price = item_data['sale_price']
                sale_item.purchase_price = item_data['purchase_price']
                sale_item.profit = (item_data['sale_price'] - item_data['purchase_price']) * item_data['quantity']
                
                # Update stock (add back original quantity, subtract new quantity)
                db_item = Item.query.get(item_data['item_id'])
                if not db_item:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': f'Item with ID {item_data["item_id"]} not found'}), 400
                
                db_item.quantity += (original_quantity - item_data['quantity'])
                
                existing_item_ids.add(sale_item.id)
            else:  # New item
                # Add new sale item
                sale_item = SaleItem(
                    sale_id=sale.id,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity'],
                    unit=item_data['unit'],
                    purchase_price=item_data['purchase_price'],
                    sale_price=item_data['sale_price'],
                    profit=(item_data['sale_price'] - item_data['purchase_price']) * item_data['quantity']
                )
                db.session.add(sale_item)
                
                # Update stock
                db_item = Item.query.get(item_data['item_id'])
                if not db_item:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': f'Item with ID {item_data["item_id"]} not found'}), 400
                
                if db_item.quantity < item_data['quantity']:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': f'Not enough stock for {db_item.name}'}), 400
                
                db_item.quantity -= item_data['quantity']
        
        # Remove any items that were in the original sale but not in the update
        for original_item in sale.items:
            if original_item.id not in existing_item_ids:
                # Return stock for deleted items
                db_item = Item.query.get(original_item.item_id)
                if db_item:
                    db_item.quantity += original_item.quantity
                db.session.delete(original_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sale updated successfully',
            'bill_number': sale.bill_number,
            'sale_id': sale.id
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Sale update failed: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to update sale: {str(e)}'
        }), 500

@app.route('/sales/<int:id>/delete', methods=['POST'])
def delete_sale(id):
    sale = Sale.query.get_or_404(id)
    try:
        db.session.delete(sale)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Customer Management
@app.route('/customers')
@login_required
def customers():
    search_term = request.args.get('search', '')
    
    if search_term:
        customers = Customer.query.filter(
            (Customer.name.ilike(f'%{search_term}%')) | 
            (Customer.mobile.ilike(f'%{search_term}%')) | 
            (Customer.address.ilike(f'%{search_term}%'))
        ).order_by(Customer.name).all()
    else:
        customers = Customer.query.order_by(Customer.name).all()
    
    # Calculate total due for each customer and overall total
    total_due_all = 0
    for customer in customers:
        sales = Sale.query.filter_by(customer_id=customer.id).all()
        payments = Payment.query.filter_by(customer_id=customer.id).all()
        customer.total_due = sum(sale.due_amount for sale in sales) - sum(payment.amount for payment in payments)
        total_due_all += customer.total_due if customer.total_due > 0 else 0
    
    return render_template('customers.html', 
                         customers=customers, 
                         search_term=search_term,
                         total_due_all=total_due_all)


@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        try:
            # Validate required fields
            if not request.form.get('name'):
                flash('Customer name is required', 'danger')
                return redirect(url_for('add_customer'))
            
            new_customer = Customer(
                name=request.form['name'],
                mobile=request.form.get('mobile', ''),
                address=request.form.get('address', ''),
                aadhar=request.form.get('aadhar', ''),
                date_added=date.today()
            )
            
            # Handle file upload
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename != '':
                    if not allowed_file(file.filename):
                        flash('Only image files (png, jpg, jpeg, gif) are allowed', 'danger')
                        return redirect(url_for('add_customer'))
                    
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    new_customer.photo_path = f"uploads/{unique_filename}"
            
            db.session.add(new_customer)
            db.session.commit()
            
            flash('Customer added successfully', 'success')
            return redirect(url_for('view_customer', id=new_customer.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding customer: {str(e)}', 'danger')
    
    return render_template('add_customer.html')


@app.route('/api/customers/add', methods=['POST'])
@login_required
def api_add_customer():
    try:
        data = request.get_json()
        if not data.get('name'):
            return jsonify({"success": False, "message": "Customer name is required"}), 400

        new_customer = Customer(
            name=data['name'],
            mobile=data.get('mobile', ''),
            address=data.get('address', ''),
            date_added=date.today()
        )

        db.session.add(new_customer)
        db.session.commit()

        return jsonify({
            "success": True,
            "customer": {
                "id": new_customer.id,
                "name": new_customer.name,
                "mobile": new_customer.mobile
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            customer.name = request.form['name']
            customer.mobile = request.form.get('mobile', '')
            customer.address = request.form.get('address', '')
            customer.aadhar = request.form.get('aadhar', '')
            
            # Handle file upload
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename != '':
                    if not allowed_file(file.filename):
                        flash('Only image files (png, jpg, jpeg, gif) are allowed', 'danger')
                        return redirect(url_for('edit_customer', id=id))
                    
                    # Remove old photo if exists
                    if customer.photo_path:
                        try:
                            os.remove(os.path.join('static', customer.photo_path))
                        except Exception as e:
                            app.logger.error(f"Error deleting old photo: {str(e)}")
                    
                    # Save new photo
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    customer.photo_path = f"uploads/{unique_filename}"
            
            db.session.commit()
            flash('Customer updated successfully', 'success')
            return redirect(url_for('view_customer', id=customer.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'danger')
    
    return render_template('edit_customer.html', customer=customer)


@app.route('/customers/delete/<int:id>', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    
    try:
        # Delete related payments first
        Payment.query.filter_by(customer_id=id).delete()
        
        # Update related sales to remove customer reference
        Sale.query.filter_by(customer_id=id).update({'customer_id': None})
        
        # Delete customer photo if exists
        if customer.photo_path:
            try:
                os.remove(os.path.join('static', customer.photo_path))
            except Exception as e:
                app.logger.error(f"Error deleting customer photo: {str(e)}")
        
        # Delete the customer
        db.session.delete(customer)
        db.session.commit()
        
        flash('Customer deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'danger')
    
    return redirect(url_for('customers'))


@app.route('/customers/<int:customer_id>/add_payment', methods=['POST'])
@login_required
def add_payment(customer_id):
    try:
        amount = float(request.form['amount'])
        payment_date = datetime.strptime(request.form['payment_date'], '%Y-%m-%d').date()
        description = request.form.get('description', '')
        
        new_payment = Payment(
            customer_id=customer_id,
            amount=amount,
            payment_date=payment_date,
            description=description
        )
        
        db.session.add(new_payment)
        db.session.commit()
        
        flash('Payment added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding payment: {str(e)}', 'danger')
    
    return redirect(url_for('view_customer', id=customer_id))

@app.route('/customers/<int:customer_id>/payments/<int:payment_id>/edit', methods=['POST'])
@login_required
def edit_payment(customer_id, payment_id):
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        # Verify this payment belongs to the customer
        if payment.customer_id != customer_id:
            flash('Payment does not belong to this customer', 'danger')
            return redirect(url_for('view_customer', id=customer_id))
        
        amount = float(request.form['amount'])
        payment_date = datetime.strptime(request.form['payment_date'], '%Y-%m-%d').date()
        description = request.form.get('description', '')
        
        payment.amount = amount
        payment.payment_date = payment_date
        payment.description = description
        
        db.session.commit()
        
        flash('Payment updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating payment: {str(e)}', 'danger')
    
    return redirect(url_for('view_customer', id=customer_id))

@app.route('/payments/delete/<int:id>', methods=['POST'])
@login_required
def delete_payment(id):
    payment = Payment.query.get_or_404(id)
    customer_id = payment.customer_id
    
    try:
        db.session.delete(payment)
        db.session.commit()
        flash('Payment deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting payment: {str(e)}', 'danger')
    
    return redirect(url_for('view_customer', id=customer_id))


@app.route('/customers/<int:id>')
@login_required
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    
    # Calculate customer balance
    sales = Sale.query.filter_by(customer_id=id).all()
    payments = Payment.query.filter_by(customer_id=id).all()
    customer_balance = sum(sale.due_amount for sale in sales) - sum(payment.amount for payment in payments)
    
    # Prepare ledger entries
    ledger = []
    balance = 0
    
    # Add sales to ledger
    for sale in sales:
        balance += sale.due_amount
        ledger.append({
            'date': sale.sale_date,
            'description': f'Sale #{sale.bill_number}',
            'amount': sale.total_amount,
            'payment': sale.received_amount,
            'balance': balance,
            'payment_id': None  # Sales don't have payment IDs
        })
    
    # Add payments to ledger
    for payment in payments:
        balance -= payment.amount
        ledger.append({
            'date': payment.payment_date,
            'description': payment.description or 'Payment',
            'amount': 0,
            'payment': payment.amount,
            'balance': balance,
            'payment_id': payment.id  # Include payment ID for editing
        })
    
    # Sort ledger by date
    ledger.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('view_customer.html',
                         customer=customer,
                         customer_balance=customer_balance,
                         ledger=ledger,
                         sales=sales,
                         payments=payments,
                         date=date)

@app.route('/customers/<int:id>/clear_ledger', methods=['POST'])
@login_required
def clear_ledger(id):
    customer = Customer.query.get_or_404(id)
    
    # Calculate customer balance
    sales = Sale.query.filter_by(customer_id=id).all()
    payments = Payment.query.filter_by(customer_id=id).all()
    customer_balance = sum(sale.due_amount for sale in sales) - sum(payment.amount for payment in payments)
    
    # Check if balance is zero
    if abs(customer_balance) > 0.01:
        flash('Cannot clear ledger: Customer balance is not zero', 'danger')
        return redirect(url_for('view_customer', id=id))
    
    try:
        # 1. Update all sales: remove customer association AND mark as fully paid
        for sale in sales:
            sale.customer_id = None  # Remove customer association
            if sale.due_amount > 0:  # If there was any due amount
                sale.received_amount = sale.total_amount  # Mark as fully paid
                sale.due_amount = 0.0  # Set due to zero
        
        # 2. Delete all payment records for this customer
        Payment.query.filter_by(customer_id=id).delete()
        
        db.session.commit()
        flash('Ledger cleared successfully. All sales converted to Walk-in customer records, marked as paid, and payment records removed.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing ledger: {str(e)}', 'danger')
    
    return redirect(url_for('view_customer', id=id))

# Supplier Management
@app.route('/suppliers')
@login_required
def suppliers():
    search_term = request.args.get('search', '')
    
    if search_term:
        suppliers = Supplier.query.filter(
            (Supplier.name.ilike(f'%{search_term}%')) | 
            (Supplier.mobile.ilike(f'%{search_term}%')) | 
            (Supplier.gstin.ilike(f'%{search_term}%'))
        ).order_by(Supplier.name).all()
    else:
        suppliers = Supplier.query.order_by(Supplier.name).all()
    
    return render_template('suppliers.html', 
                         suppliers=suppliers, 
                         search_term=search_term)

@app.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        try:
            name = request.form['name']
            if not name:
                flash('Supplier name is required', 'danger')
                return redirect(url_for('add_supplier'))
            
            new_supplier = Supplier(
                name=name,
                mobile=request.form.get('mobile', ''),
                address=request.form.get('address', ''),
                gstin=request.form.get('gstin', ''),
                date_added=date.today()
            )
            
            db.session.add(new_supplier)
            db.session.commit()
            
            flash('Supplier added successfully', 'success')
            return redirect(url_for('view_supplier', id=new_supplier.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding supplier: {str(e)}', 'danger')
    
    return render_template('add_supplier.html')

@app.route('/suppliers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            supplier.name = request.form['name']
            supplier.mobile = request.form.get('mobile', '')
            supplier.address = request.form.get('address', '')
            supplier.gstin = request.form.get('gstin', '')
            
            db.session.commit()
            flash('Supplier updated successfully', 'success')
            return redirect(url_for('view_supplier', id=supplier.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating supplier: {str(e)}', 'danger')
    
    return render_template('edit_supplier.html', supplier=supplier)

@app.route('/suppliers/delete/<int:id>', methods=['POST'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    
    try:
        # Update related items to remove supplier reference
        Item.query.filter_by(supplier_id=id).update({'supplier_id': None})
        
        db.session.delete(supplier)
        db.session.commit()
        
        flash('Supplier deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting supplier: {str(e)}', 'danger')
    
    return redirect(url_for('suppliers'))


@app.route('/suppliers/<int:id>')
@login_required
def view_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    items = Item.query.filter_by(supplier_id=id).all()
    
    # Get transactions sorted by date (descending)
    transactions = SupplierTransaction.query.filter_by(supplier_id=id)\
        .order_by(SupplierTransaction.date.desc())\
        .all()
    
    # Get only the last 10 transactions
    recent_transactions = transactions[:10] if transactions else []
    
    # Ensure balance is not None
    current_balance = supplier.balance if supplier.balance is not None else 0
    
    return render_template('view_supplier.html',
                         supplier=supplier,
                         items=items,
                         transactions=recent_transactions,
                         current_balance=current_balance)


# Supplier Transactions
@app.route('/suppliers/<int:supplier_id>/add_transaction', methods=['GET', 'POST'])
@login_required
def add_supplier_transaction(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    if request.method == 'POST':
        try:
            transaction_type = request.form['transaction_type']
            amount = float(request.form['amount'])
            description = request.form.get('description', '')
            bill_no = request.form.get('bill_no', '')
            transaction_date = datetime.strptime(request.form['transaction_date'], '%Y-%m-%d').date()
            
            new_transaction = SupplierTransaction(
                supplier_id=supplier_id,
                date=transaction_date,
                bill_no=bill_no,
                description=description,
                amount=amount,
                transaction_type=transaction_type
            )
            
            # Update supplier balance
            if transaction_type == 'purchase':
                supplier.balance += amount
            else:  # payment
                supplier.balance -= amount
            
            db.session.add(new_transaction)
            db.session.commit()
            
            flash('Transaction added successfully', 'success')
            return redirect(url_for('view_supplier', id=supplier_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding transaction: {str(e)}', 'danger')
    
    # Pass the current date to the template
    return render_template('add_supplier_transaction.html', 
                         supplier=supplier,
                         current_date=date.today().strftime('%Y-%m-%d'))

@app.route('/suppliers/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier_transaction(transaction_id):
    transaction = SupplierTransaction.query.get_or_404(transaction_id)
    supplier = transaction.supplier
    
    if request.method == 'POST':
        try:
            old_amount = transaction.amount
            old_type = transaction.transaction_type
            
            transaction.transaction_type = request.form['transaction_type']
            transaction.amount = float(request.form['amount'])
            transaction.description = request.form.get('description', '')
            transaction.bill_no = request.form.get('bill_no', '')
            transaction.date = datetime.strptime(request.form['transaction_date'], '%Y-%m-%d').date()
            
            # First reverse the old transaction's effect
            if old_type == 'purchase':
                supplier.balance -= old_amount
            else:  # payment
                supplier.balance += old_amount
            
            # Then apply the new transaction
            if transaction.transaction_type == 'purchase':
                supplier.balance += transaction.amount
            else:  # payment
                supplier.balance -= transaction.amount
            
            db.session.commit()
            
            flash('Transaction updated successfully', 'success')
            return redirect(url_for('view_supplier', id=supplier.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating transaction: {str(e)}', 'danger')
    
    return render_template('edit_supplier_transaction.html', 
                         transaction=transaction,
                         supplier=supplier)

@app.route('/suppliers/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_supplier_transaction(transaction_id):
    transaction = SupplierTransaction.query.get_or_404(transaction_id)
    supplier = transaction.supplier
    
    try:
        # Reverse the transaction's effect on balance
        if transaction.transaction_type == 'purchase':
            supplier.balance -= transaction.amount
        else:  # payment
            supplier.balance += transaction.amount
        
        db.session.delete(transaction)
        db.session.commit()
        
        flash('Transaction deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting transaction: {str(e)}', 'danger')
    
    return redirect(url_for('view_supplier', id=supplier.id))


@app.route('/suppliers/<int:supplier_id>/statement')
@login_required
def supplier_statement(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    transactions = SupplierTransaction.query.filter_by(supplier_id=supplier_id)\
        .order_by(SupplierTransaction.date, SupplierTransaction.id).all()
    
    # Calculate running balance
    balance = 0
    statement = []
    for t in transactions:
        if t.transaction_type == 'purchase':
            balance += t.amount
        else:  # payment
            balance -= t.amount
        statement.append({
            'date': t.date,
            'bill_no': t.bill_no,
            'description': t.description,
            'purchase': t.amount if t.transaction_type == 'purchase' else 0,
            'payment': t.amount if t.transaction_type == 'payment' else 0,
            'balance': balance
        })
    
    # Ensure we're passing the correct balance (supplier.balance might be None)
    current_balance = supplier.balance if supplier.balance is not None else 0
    
    return render_template('supplier_statement.html',
                         supplier=supplier,
                         statement=statement,
                         balance=current_balance)

@app.route('/suppliers/<int:id>/clear_ledger', methods=['POST'])
@login_required
def clear_supplier_ledger(id):
    supplier = Supplier.query.get_or_404(id)
    
    # Check if supplier balance is zero (with small tolerance for floating point)
    if abs(supplier.balance or 0) > 0.01:
        flash('Cannot clear ledger: Supplier balance is not zero', 'danger')
        return redirect(url_for('view_supplier', id=id))
    
    try:
        # Delete all transaction records for this supplier
        SupplierTransaction.query.filter_by(supplier_id=id).delete()
        
        # Reset supplier balance to zero
        supplier.balance = 0.0
        
        db.session.commit()
        flash('Supplier ledger cleared successfully. All transaction records removed.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing supplier ledger: {str(e)}', 'danger')
        app.logger.error(f'Error clearing supplier ledger for supplier {id}: {str(e)}')
    
    return redirect(url_for('view_supplier', id=id))


# Reports
@app.route('/reports/sales')
@login_required
def sales_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date', date.today().isoformat())
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            sales = Sale.query.filter(
                Sale.sale_date >= start_date,
                Sale.sale_date <= end_date
            ).order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(30).all()
            
            total_sales = sum(sale.total_amount for sale in sales)
            total_profit = sum(sale.total_profit for sale in sales)
            total_received = sum(sale.received_amount for sale in sales)
            total_due = sum(sale.due_amount for sale in sales)
            
            return render_template('sales_report.html', 
                                sales=sales,
                                start_date=start_date,
                                end_date=end_date,
                                total_sales=total_sales,
                                total_profit=total_profit,
                                total_received=total_received,
                                total_due=total_due)
        except ValueError:
            flash('Invalid date format', 'danger')
    
    # Default to last 30 days if no dates provided
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    sales = Sale.query.filter(
        Sale.sale_date >= start_date,
        Sale.sale_date <= end_date
    ).order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(30).all()
    
    total_sales = sum(sale.total_amount for sale in sales)
    total_profit = sum(sale.total_profit for sale in sales)
    total_received = sum(sale.received_amount for sale in sales)
    total_due = sum(sale.due_amount for sale in sales)
    
    return render_template('sales_report.html', 
                         sales=sales,
                         start_date=start_date,
                         end_date=end_date,
                         total_sales=total_sales,
                         total_profit=total_profit,
                         total_received=total_received,
                         total_due=total_due)

# AJAX endpoints for sales processing
@app.route('/api/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_id = request.json.get('item_id')
    quantity = float(request.json.get('quantity', 1))
    
    item = Item.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'})
    
    if quantity <= 0:
        return jsonify({'success': False, 'message': 'Quantity must be positive'})
    
    if quantity > item.quantity:
        return jsonify({'success': False, 'message': f'Not enough stock. Available: {item.quantity} {item.unit}'})
    
    # Get or initialize cart in session
    cart = session.get('sale_cart', [])
    
    # Check if item already in cart
    item_in_cart = next((i for i in cart if i['item_id'] == item_id), None)
    
    if item_in_cart:
        item_in_cart['quantity'] += quantity
    else:
        cart.append({
            'item_id': item.id,
            'id': item.id,  # Make sure this is included
            'name': item.name,
            'quantity': quantity,
            'unit': item.unit,
            'purchase_price': item.purchase_price,  # This is critical
            'sale_price': item.sale_price,
            'price': item.sale_price  # For compatibility
        })
    
    session['sale_cart'] = cart
    
    return jsonify({
        'success': True,
        'cart': cart,
        'cart_count': len(cart),
        'subtotal': sum(item['quantity'] * item['sale_price'] for item in cart)
    })

@app.route('/api/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    item_id = request.json.get('item_id')
    
    cart = session.get('sale_cart', [])
    cart = [item for item in cart if item['item_id'] != item_id]
    
    session['sale_cart'] = cart
    
    return jsonify({
        'success': True,
        'cart': cart,
        'cart_count': len(cart),
        'subtotal': sum(item['quantity'] * item['sale_price'] for item in cart)
    })

@app.route('/api/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    session.pop('sale_cart', None)
    return jsonify({'success': True})

# Create tables and admin user
with app.app_context():
    db.create_all()
    create_admin_user()

if __name__ == '__main__':
    app.run(debug=True)
