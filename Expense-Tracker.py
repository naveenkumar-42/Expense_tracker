import tkinter as tk
import customtkinter as ctk
from PIL import ImageTk, Image
import mysql.connector
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from tkinter import filedialog
import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime
import calendar
import atexit
import logging
import sys

# Configure logging
def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, "expense_tracker.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('ExpenseTracker')
    return logger

# Initialize logger
logger = setup_logging()

# Load environment variables
load_dotenv()

# Configure Gemini AI (Optional)
GOOGLE_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
has_ai_features = False
model = None  # <-- Add this line
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        models = genai.list_models()
        for m in models:
            print(m.name)
        model = genai.GenerativeModel('models/gemini-1.0-pro-latest')
        has_ai_features = True
    except Exception as e:
        logger.warning(f"Could not initialize AI features: {e}")
else:
    logger.info("AI features are disabled. Set GOOGLE_GEMINI_API_KEY in .env file to enable them.")

# Global variable for database connection
conn = None

# Initialize database connection
def create_db_connection():
    global conn
    try:
        logger.info("Attempting to connect to database...")
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            database = 'student',
            password="",
            port=3306,
        )
        
        cursor = conn.cursor()
        logger.info("Creating database if it doesn't exist...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS expense_tracker")
        cursor.execute("USE expense_tracker")
        
        create_tables()
        
        logger.info("Database connection successful")
        return conn
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            logger.error("Invalid database username or password")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            logger.error("Database does not exist")
        else:
            logger.error(f"MySQL Error: {err}")
        return None
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def create_tables():
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS userinfo (
                userid VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255) NOT NULL,
                user_name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL DEFAULT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense (
                id INT AUTO_INCREMENT PRIMARY KEY,
                userid VARCHAR(255) NOT NULL,
                date VARCHAR(20) NOT NULL,
                expense_type VARCHAR(255) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (userid) REFERENCES userinfo(userid) ON DELETE CASCADE,
                CHECK (amount > 0)
            )
        """)
        
        conn.commit()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

def cleanup_connection():
    global conn
    try:
        if conn and hasattr(conn, 'is_connected') and conn.is_connected():
            conn.close()
            logger.info("Database connection closed properly")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")

# Register cleanup function
atexit.register(cleanup_connection)

# Initialize database connection
conn = create_db_connection()
if not conn:
    logger.warning("Could not establish database connection. Some features may not work.")

def ensure_connection():
    global conn
    try:
        if conn and hasattr(conn, 'is_connected') and not conn.is_connected():
            conn = create_db_connection()
        elif not conn:
            conn = create_db_connection()
    except Exception as e:
        logger.error(f"Error reconnecting to database: {e}")
        return False
    return bool(conn and hasattr(conn, 'is_connected') and conn.is_connected())

# Create main application window
app = ctk.CTk()
ctk.set_default_color_theme("green")
app.geometry("1200x800")
app.minsize(1000, 700)
app._fg_color = "#F5F5F5"
app.title("Expense Tracker")

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

# Center the main window
center_window(app, 1200, 800)

# Helper function to create CTkImage
def create_ctk_image(path, size):
    try:
        img = Image.open(path)
        img = img.resize(size)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception as e:
        logger.error(f"Error loading image {path}: {e}")
        return None

class InputValidator:
    @staticmethod
    def validate_amount(amount_str):
        """Validate amount input"""
        try:
            amount = float(amount_str)
            if amount <= 0:
                return False, "Amount must be greater than 0"
            return True, amount
        except ValueError:
            return False, "Amount must be a valid number"

    @staticmethod
    def validate_date(date_str):
        """Validate date input"""
        try:
            date = datetime.strptime(date_str, "%d/%m/%Y")
            if date > datetime.now():
                return False, "Date cannot be in the future"
            return True, date
        except ValueError:
            return False, "Invalid date format. Please use dd/mm/yyyy"

    @staticmethod
    def validate_userid(userid):
        """Validate user ID"""
        if not userid or len(userid) < 3:
            return False, "User ID must be at least 3 characters long"
        if not userid.isalnum():
            return False, "User ID must contain only letters and numbers"
        return True, userid

    @staticmethod
    def validate_password(password):
        """Validate password"""
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long"
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        return True, password

def first_page():
    def submit():
        if not ensure_connection():
            tk.messagebox.showerror("Error", "Database connection is not available")
            return
    
        get_userid = userid_entry.get().strip()
        get_password = password_entry.get()

        if not get_userid or not get_password:
            tk.messagebox.showerror("Login", "Username and password are required")
            return

        try:
            logger.info(f"Attempting login for user: {get_userid}")
            cur = conn.cursor()
            cur.execute("SELECT userid, password FROM userinfo WHERE userid = %s", (get_userid,))
            user = cur.fetchone()
            
            if user:
                logger.info("User found in database")
                if user[1] == get_password:
                    logger.info("Password matches, login successful")
                    cur.execute("UPDATE userinfo SET last_login = CURRENT_TIMESTAMP WHERE userid = %s", (get_userid,))
                    conn.commit()
                    second_page(frame1, get_userid)
                else:
                    logger.warning("Password mismatch for user")
                    tk.messagebox.showerror("Login", "Invalid credentials")
            else:
                logger.warning(f"No user found with ID: {get_userid}")
                tk.messagebox.showerror("Login", "Invalid credentials")
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            tk.messagebox.showerror("Database Error", f"Error accessing database: {str(e)}")

    def signUp_page_call():
        signUp_page(frame1)

    def toggle_password_visibility():
        current_show = password_entry.cget("show")
        if current_show == "•":
            password_entry.configure(show="")
            toggle_btn.configure(text="👁️")
        else:
            password_entry.configure(show="•")
            toggle_btn.configure(text="👁")

    frame1 = ctk.CTkFrame(app, fg_color="#2E8BC0")
    frame1.pack(fill="both", expand=True)
    
    # Main heading with white text - Centered
    main_label = ctk.CTkLabel(
        master=frame1,
        text="Take control of your expenses,\nunlock financial freedom",
        font=("Helvetica", 36, "bold"),
        text_color="#FFFFFF"
    )
    main_label.place(relx=0.5, rely=0.1, anchor="center")  # Changed to center

    # Login frame
    frame2 = ctk.CTkFrame(
        frame1,
        width=350,
        height=400,
        corner_radius=10,
        fg_color="#FFFFFF",
        border_width=0
    )
    frame2.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    # Login title
    login_label = ctk.CTkLabel(
        master=frame2,
        text="LOGIN",
        font=("Helvetica", 24, "bold"),
        text_color="#000000"
    )
    login_label.place(relx=0.5, rely=0.1, anchor="center")

    # Username field
    username_label = ctk.CTkLabel(
        master=frame2,
        text="USERNAME",
        font=("Helvetica", 14),
        text_color="#000000"
    )
    username_label.place(relx=0.1, rely=0.25)
    
    userid_entry = ctk.CTkEntry(
        master=frame2,
        width=280,
        height=35,
        placeholder_text="Enter Username",
        corner_radius=5,
        border_color="#E0E0E0"
    )
    userid_entry.place(relx=0.1, rely=0.32)

    # Password field
    password_label = ctk.CTkLabel(
        master=frame2,
        text="PASSWORD",
        font=("Helvetica", 14),
        text_color="#000000"
    )
    password_label.place(relx=0.1, rely=0.45)

    # Password entry with toggle button
    password_entry = ctk.CTkEntry(
        master=frame2,
        width=280,
        height=35,
        placeholder_text="Enter Password",
        show="•",
        corner_radius=5,
        border_color="#E0E0E0"
    )
    password_entry.place(relx=0.1, rely=0.52)

    # Password visibility toggle button
    toggle_btn = ctk.CTkButton(
        master=frame2,
        width=30,
        height=35,
        text="👁",
        corner_radius=5,
        fg_color="#E0E0E0",
        hover_color="#CCCCCC",
        text_color="#000000",
        command=toggle_password_visibility
    )
    toggle_btn.place(relx=0.85, rely=0.52)

    # Login button
    login_btn = ctk.CTkButton(
        master=frame2,
        width=280,
        height=40,
        text="LOGIN",
        corner_radius=5,
        fg_color="#2E8BC0",
        hover_color="#1B5A89",
        font=("Helvetica", 14, "bold"),
        command=submit
    )
    login_btn.place(relx=0.1, rely=0.7)

    # Sign up link
    signup_label = ctk.CTkLabel(
        master=frame2,
        text="NEW USER? CREATE ACCOUNT",
        font=("Helvetica", 12),
        text_color="#2E8BC0",
        cursor="hand2"
    )
    signup_label.place(relx=0.5, rely=0.85, anchor="center")
    signup_label.bind("<Button-1>", lambda e: signUp_page_call())

    # Make the signup text clickable
    def on_enter(e):
        signup_label.configure(font=("Helvetica", 12, "underline"))
    
    def on_leave(e):
        signup_label.configure(font=("Helvetica", 12))
    
    signup_label.bind("<Enter>", on_enter)
    signup_label.bind("<Leave>", on_leave)

def second_page(frame1, userid):
    frame1.destroy()
    frame3 = ctk.CTkFrame(app, fg_color="#2E8BC0")
    frame3.pack(fill="both", expand=True)
    
    # Add AI button at the top right
    ai_btn = ctk.CTkButton(
        master=frame3,
        text="💡 Ask AI",
        width=120,
        height=35,
        fg_color="#FFD700",
        hover_color="#FFC300",
        text_color="#000000",
        font=("Helvetica", 14, "bold"),
        command=open_ai_chat_window
    )
    ai_btn.place(relx=0.85, rely=0.02)

    # Create frames
    frame4 = ctk.CTkFrame(
        frame3, 
        width=400, 
        height=700,  # Increased height
        fg_color="#FFFFFF", 
        border_width=0, 
        corner_radius=10
    )
    frame4.place(relx=0.05, rely=0.12)  # Adjusted y position
    
    frame5 = ctk.CTkFrame(
        frame3, 
        width=700, 
        height=700,  # Increased height to match frame4
        fg_color="#FFFFFF", 
        border_width=0, 
        corner_radius=10
    )
    frame5.place(relx=0.4, rely=0.12)  # Adjusted y position
    
    frame6 = ctk.CTkFrame(
        frame5, 
        width=660, 
        height=450,  # Increased height
        fg_color="#FFFFFF", 
        border_width=0
    )
    frame6.place(relx=0.05, rely=0.05)
    
    frame7 = ctk.CTkFrame(
        frame5, 
        width=660, 
        height=180,  # Increased height
        fg_color="#FFFFFF", 
        border_width=0
    )
    frame7.place(relx=0.05, rely=0.72)  # Adjusted y position

    def data():
        if not ensure_connection():
            tk.messagebox.showerror("Error", "Database connection is not available")
            return
        
        try:
            # Clear any existing plots
            plt.close('all')
            
            # Get user data
            cur = conn.cursor()
            cur.execute("SELECT * FROM expense WHERE userid = %s", (userid,))
            rows = cur.fetchall()
            
            # Clear existing widgets in frame6
            for widget in frame6.winfo_children():
                widget.destroy()
            
            if not rows:
                # Show "No data" message if there are no transactions
                no_data_label = ctk.CTkLabel(
                    master=frame6,
                    text="No transactions yet.\nAdd your first transaction to see analytics!",
                    font=("Helvetica", 16),
                    text_color="#666666"
                )
                no_data_label.place(relx=0.5, rely=0.5, anchor="center")
                
                # Clear summary frame
                for widget in frame7.winfo_children():
                    widget.destroy()
                    
                summary_grid = ctk.CTkFrame(frame7, fg_color="#FFFFFF")
                summary_grid.pack(fill="both", expand=True, padx=20, pady=10)
                
                # Show zero values in summary
                create_summary_labels(summary_grid, 0, 0)
                return
            
            # Initialize variables
            categories = {
                "Food & Dining": 0,
                "Transportation": 0,
                "Housing": 0,
                "Entertainment": 0,
                "Other": 0
            }
            Income = 0
            total_expense = 0
            
            # Process the data
            for row in rows:
                try:
                    amount = float(row[4])
                    expense_type = row[3]
                    
                    if expense_type == "Income":
                        Income += amount
                    else:
                        if expense_type in categories:
                            categories[expense_type] += amount
                            total_expense += amount
                except (ValueError, IndexError) as e:
                    logger.error(f"Error processing row {row}: {e}")
                    continue
            
            # Create figure with proper styling
            plt.style.use('default')
            fig = plt.figure(figsize=(12, 5))
            fig.patch.set_facecolor('#FFFFFF')
            
            try:
                # Create pie chart if there are expenses
                if total_expense > 0:
                    ax1 = plt.subplot(121)
                    ax1.set_facecolor('#FFFFFF')
                    
                    # Filter out zero values
                    non_zero_categories = {k: v for k, v in categories.items() if v > 0}
                    sizes = list(non_zero_categories.values())
                    labels = list(non_zero_categories.keys())
                    colors = ["#F1C40F", "#2ECC71", "#E74C3C", "#3498DB", "#9B59B6"][:len(non_zero_categories)]
                    explode = [0.05] * len(non_zero_categories)
                    
                    if sizes:  # Only create pie chart if there are non-zero values
                        wedges, texts, autotexts = ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                               autopct=lambda pct: f'₹{int(pct/100.*sum(sizes)):,}\n({pct:.1f}%)',
                               shadow=False, startangle=90)
                        
                        plt.setp(autotexts, size=8, weight="bold")
                        plt.setp(texts, size=8)
                        ax1.set_title("Expense Distribution", pad=20, fontsize=12, fontweight='bold')
                
                # Create bar chart
                ax2 = plt.subplot(122)
                ax2.set_facecolor('#FFFFFF')
                
                # Prepare data for bar chart
                all_categories = {k: v for k, v in categories.items() if v > 0}
                if Income > 0:
                    all_categories["Income"] = Income
                    
                if all_categories:  # Only create bar chart if there are values
                    x = list(all_categories.keys())
                    y = list(all_categories.values())
                    
                    bars = ax2.bar(x, y, color=["#2ECC71" if cat == "Income" else "#E74C3C" for cat in x])
                    
                    ax2.set_title("Income vs Expenses", pad=20, fontsize=12, fontweight='bold')
                    ax2.set_xlabel("Categories", labelpad=10)
                    ax2.set_ylabel("Amount (₹)", labelpad=10)
                    
                    plt.xticks(rotation=30, ha='right')
                    
                    for bar in bars:
                        height = bar.get_height()
                        ax2.text(bar.get_x() + bar.get_width()/2., height,
                                f'₹{int(height):,}',
                                ha='center', va='bottom', fontsize=8)
                
                # Adjust layout
                plt.tight_layout(pad=3.0)
                
                # Create canvas and display charts
                canvas = FigureCanvasTkAgg(fig, master=frame6)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
                
            except Exception as e:
                logger.error(f"Error creating charts: {e}")
                error_label = ctk.CTkLabel(
                    master=frame6,
                    text="Error creating charts.\nPlease try again.",
                    font=("Helvetica", 16),
                    text_color="#E74C3C"
                )
                error_label.place(relx=0.5, rely=0.5, anchor="center")
            
            # Update summary frame
            for widget in frame7.winfo_children():
                widget.destroy()
            
            summary_grid = ctk.CTkFrame(frame7, fg_color="#FFFFFF")
            summary_grid.pack(fill="both", expand=True, padx=20, pady=10)
            
            create_summary_labels(summary_grid, Income, total_expense)
            
        except Exception as e:
            logger.error(f"An error occurred while creating the visualizations: {str(e)}")
            tk.messagebox.showerror("Error", f"An error occurred while creating the visualizations: {str(e)}")

    def create_summary_labels(summary_grid, income, total_expense):
        # Income column
        income_frame = ctk.CTkFrame(summary_grid, fg_color="#FFFFFF")
        income_frame.pack(side="left", expand=True, fill="both", padx=10)
        
        income_label = ctk.CTkLabel(
            master=income_frame,
            text="Total Income",
            font=("Helvetica", 16, "bold"),
            text_color="#000000"
        )
        income_label.pack(pady=(10, 5))
        
        income_value_label = ctk.CTkLabel(
            master=income_frame,
            text=f"₹{income:,.2f}",
            font=("Helvetica", 20, "bold"),
            text_color="#27AE60"
        )
        income_value_label.pack()
        
        # Expense column
        expense_frame = ctk.CTkFrame(summary_grid, fg_color="#FFFFFF")
        expense_frame.pack(side="right", expand=True, fill="both", padx=10)
        
        expense_label = ctk.CTkLabel(
            master=expense_frame,
            text="Total Expense",
            font=("Helvetica", 16, "bold"),
            text_color="#000000"
        )
        expense_label.pack(pady=(10, 5))
        
        expense_value_label = ctk.CTkLabel(
            master=expense_frame,
            text=f"₹{total_expense:,.2f}",
            font=("Helvetica", 20, "bold"),
            text_color="#E74C3C"
        )
        expense_value_label.pack()

    def submit_expense():
        try:
            if not ensure_connection():
                tk.messagebox.showerror("Error", "Database connection is not available")
                return
            
            get_amount = amount_entry.get().strip()
            get_expense_type = expense_type_combobox.get()
            get_date = date_entry.get().strip()
            get_comments = comment_entry.get().strip()
            
            # Validate amount
            valid, result = InputValidator.validate_amount(get_amount)
            if not valid:
                tk.messagebox.showerror("Error", result)
                return
            amount = result
            
            # Validate date
            valid, result = InputValidator.validate_date(get_date)
            if not valid:
                tk.messagebox.showerror("Error", result)
                return
            
            # Format the display text
            transaction_type = "➕ Income" if get_expense_type == "Income" else f"➖ {get_expense_type}"
            show_data = f"{transaction_type}\nAmount: ₹{amount:,.2f}\nDate: {get_date}"
            if get_comments:
                show_data += f"\nNotes: {get_comments}"
            
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO expense (userid, date, expense_type, amount, comment) VALUES (%s, %s, %s, %s, %s)",
                (userid, get_date, get_expense_type, amount, get_comments)
            )
            conn.commit()
            
            txt_box.configure(state="normal")
            txt_box.insert("1.0", "="*40 + "\n" + show_data + "\n\n")
            txt_box.configure(state="disabled")
            
            # Clear input fields
            amount_entry.delete(0, ctk.END)
            comment_entry.delete(0, ctk.END)
            date_entry.delete(0, ctk.END)
            date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
            expense_type_combobox.set("Transportation")
            
            # Update charts
            data()
            
            tk.messagebox.showinfo("Success", "Transaction added successfully!")
            
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            tk.messagebox.showerror("Error", f"An error occurred: {str(e)}")

    # Add UI elements
    main_label = ctk.CTkLabel(
        master=frame4,
        text="ADD NEW TRANSACTION",
        font=("Helvetica", 20, "bold"),
        text_color="#000000",
    )
    main_label.place(relx=0.5, rely=0.05, anchor="center")

    helper_label = ctk.CTkLabel(
        master=frame4,
        text="💡 Add income by selecting 'Income' as type",
        font=("Helvetica", 12),
        text_color="#666666"
    )
    helper_label.place(relx=0.5, rely=0.1, anchor="center")
    
    history_label = ctk.CTkLabel(
        master=frame4,
        text="Recent Transactions",
        font=("Helvetica", 14, "bold"),
        text_color="#000000"
    )
    history_label.place(relx=0.05, rely=0.15)

    txt_box = ctk.CTkTextbox(
        master=frame4,
        height=250,  # Increased height
        width=360,
        fg_color="#FFFFFF",
        border_width=1,
        border_color="#E0E0E0",
        font=("Helvetica", 12),
        text_color="#000000"
    )
    txt_box.place(relx=0.05, rely=0.2)
    txt_box.configure(state="disabled")
    
    form_frame = ctk.CTkFrame(master=frame4, fg_color="#FFFFFF")
    form_frame.place(relx=0.05, rely=0.6, relwidth=0.9, relheight=0.35)  # Adjusted y position

    form_frame.grid_columnconfigure(0, weight=1)
    form_frame.grid_columnconfigure(1, weight=1)

    # Amount
    amount_label = ctk.CTkLabel(form_frame, text="AMOUNT (₹)*", font=("Helvetica", 12), text_color="#000000")
    amount_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
    amount_entry = ctk.CTkEntry(form_frame, width=160, height=30, placeholder_text="Enter amount", corner_radius=5, border_color="#E0E0E0", font=("Helvetica", 12))
    amount_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 10))

    # Type
    type_label = ctk.CTkLabel(form_frame, text="TYPE*", font=("Helvetica", 12), text_color="#000000")
    type_label.grid(row=0, column=1, sticky="w", padx=5, pady=(5, 0))
    expense_type_combobox = ctk.CTkComboBox(form_frame, values=["Food & Dining", "Transportation", "Housing", "Entertainment", "Other", "Income"], width=160, height=30, font=("Helvetica", 12), border_color="#E0E0E0", button_color="#E0E0E0", button_hover_color="#CCCCCC", dropdown_hover_color="#F0F0F0")
    expense_type_combobox.set("Transportation")
    expense_type_combobox.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 10))

    # Date
    date_label = ctk.CTkLabel(form_frame, text="DATE* (DD/MM/YYYY)", font=("Helvetica", 12), text_color="#000000")
    date_label.grid(row=2, column=0, sticky="w", padx=5, pady=(5, 0))
    date_entry = ctk.CTkEntry(form_frame, width=160, height=30, placeholder_text="dd/mm/yyyy", corner_radius=5, border_color="#E0E0E0", font=("Helvetica", 12))
    date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
    date_entry.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 10))

    # Comments
    comment_label = ctk.CTkLabel(form_frame, text="COMMENTS (OPTIONAL)", font=("Helvetica", 12), text_color="#000000")
    comment_label.grid(row=2, column=1, sticky="w", padx=5, pady=(5, 0))
    comment_entry = ctk.CTkEntry(form_frame, width=160, height=30, placeholder_text="Add notes", corner_radius=5, border_color="#E0E0E0", font=("Helvetica", 12))
    comment_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=(0, 10))

    # Submit Button
    submit_btn = ctk.CTkButton(form_frame, width=340, height=35, text="Add Transaction", corner_radius=5, fg_color="#2E8BC0", hover_color="#1B5A89", font=("Helvetica", 14, "bold"), command=submit_expense)
    submit_btn.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="ew")

    # Initial data load
    data()

def signUp_page(frame1):
    frame1.destroy()
    def go_first_page():
        first_page()
        
    def submit():
        if not ensure_connection():
            tk.messagebox.showerror("Error", "Database connection is not available")
            return
            
        get_userid = userid_entry.get().strip()
        get_name = name_entry.get().strip()
        get_password = password_entry.get()

        # Validate user ID
        valid, result = InputValidator.validate_userid(get_userid)
        if not valid:
            tk.messagebox.showerror("Sign Up", result)
            return

        # Validate password
        valid, result = InputValidator.validate_password(get_password)
        if not valid:
            tk.messagebox.showerror("Sign Up", result)
            return

        if not get_name:
            tk.messagebox.showerror("Sign Up", "Name is required")
            return

        try:
            cur = conn.cursor()
            cur.execute("SELECT userid FROM userinfo WHERE userid = %s", (get_userid,))
            if cur.fetchone():
                tk.messagebox.showerror("Sign Up", "User ID is already taken")
                return
                
            cur.execute(
                "INSERT INTO userinfo (userid, password, user_name) VALUES (%s, %s, %s)",
                (get_userid, get_password, get_name)
            )
            conn.commit()
            second_page(frame1, get_userid)
        except Exception as e:
            logger.error(f"Error creating account: {str(e)}")
            tk.messagebox.showerror("Database Error", f"Error creating account: {str(e)}")

    frame1 = ctk.CTkFrame(app, fg_color="#F5F5F5")
    frame1.pack(fill="both", expand=True)
    
    # Background image
    bg_image = create_ctk_image("background.jpg", (1200, 800))
    if bg_image:
        img1_place = ctk.CTkLabel(master=frame1, image=bg_image, text="")
        img1_place.pack(fill="both", expand=True)

    # Side image
    side_image = create_ctk_image("side.png", (400, 600))
    if side_image:
        img2_place = ctk.CTkLabel(master=frame1, image=side_image, text="")
        img2_place.place(relx=0.05, rely=0.2)

    # Main heading
    main_label = ctk.CTkLabel(
        master=frame1,
        text="Take control of your expenses,\nunlock financial freedom",
        font=("Ubuntu", 36, "bold"),
        text_color="#000000"
    )
    main_label.place(relx=0.1, rely=0.05)

    # Sign up frame with improved alignment
    frame2 = ctk.CTkFrame(
        frame1,
        width=400,  # Increased width
        height=600,  # Increased height
        corner_radius=15,
        fg_color="#FFFFFF",
        border_width=2
    )
    frame2.place(relx=0.65, rely=0.5, anchor=tk.CENTER)  # Moved to the right

    # Sign up form with better spacing
    signup_label = ctk.CTkLabel(
        master=frame2,
        text="Create Account",
        font=("Ubuntu", 28, "bold"),
        text_color="#000000"
    )
    signup_label.place(relx=0.5, rely=0.08, anchor="center")

    # Subtitle
    subtitle_label = ctk.CTkLabel(
        master=frame2,
        text="Start your financial journey today",
        font=("Ubuntu", 14),
        text_color="#666666"
    )
    subtitle_label.place(relx=0.5, rely=0.15, anchor="center")

    # Username field with improved spacing
    username_label = ctk.CTkLabel(
        master=frame2,
        text="Username",
        font=("Ubuntu", 16),
        text_color="#000000"
    )
    username_label.place(relx=0.15, rely=0.25)
    
    userid_entry = ctk.CTkEntry(
        master=frame2,
        width=300,  # Increased width
        height=40,  # Increased height
        placeholder_text="Choose a username",
        corner_radius=8
    )
    userid_entry.place(relx=0.15, rely=0.3)

    # Name field with improved spacing
    name_label = ctk.CTkLabel(
        master=frame2,
        text="Full Name",
        font=("Ubuntu", 16),
        text_color="#000000"
    )
    name_label.place(relx=0.15, rely=0.4)
    
    name_entry = ctk.CTkEntry(
        master=frame2,
        width=300,  # Increased width
        height=40,  # Increased height
        placeholder_text="Enter your full name",
        corner_radius=8
    )
    name_entry.place(relx=0.15, rely=0.45)

    # Password field with improved spacing
    password_label = ctk.CTkLabel(
        master=frame2,
        text="Password",
        font=("Ubuntu", 16),
        text_color="#000000"
    )
    password_label.place(relx=0.15, rely=0.55)

    password_entry = ctk.CTkEntry(
        master=frame2,
        width=300,  # Increased width
        height=40,  # Increased height
        placeholder_text="Create a strong password",
        show="*",
        corner_radius=8
    )
    password_entry.place(relx=0.15, rely=0.6)

    # Password requirements
    password_req = ctk.CTkLabel(
        master=frame2,
        text="Password must contain at least:\n• 6 characters\n• One uppercase letter\n• One lowercase letter\n• One number",
        font=("Ubuntu", 12),
        text_color="#666666",
        justify="left"
    )
    password_req.place(relx=0.15, rely=0.67)

    # Submit button with improved styling
    submit_btn = ctk.CTkButton(
        master=frame2,
        width=300,  # Increased width
        height=45,  # Increased height
        text="Create Account",
        corner_radius=8,
        fg_color="#2ECC71",
        hover_color="#27AE60",
        font=("Ubuntu", 16, "bold"),
        command=submit
    )
    submit_btn.place(relx=0.15, rely=0.8)

    # Login link button with improved styling
    login_btn = ctk.CTkButton(
        master=frame2,
        width=300,  # Increased width
        height=45,  # Increased height
        text="Already have an account? Log In",
        corner_radius=8,
        fg_color="#3498DB",
        hover_color="#2980B9",
        font=("Ubuntu", 16),
        command=go_first_page
    )
    login_btn.place(relx=0.15, rely=0.9)


genai.configure(api_key="AIzaSyCgX45zBv3WDH4G4sxuKAFK_eb788bgX34")

# Create a chat session with gemini-pro
model = genai.GenerativeModel('models/gemini-pro')
chat = model.start_chat(history=[])

model = genai.GenerativeModel("gemini-pro")
# chat = model.start_chat()
# response = chat.send_message("Hello!")
# print(response.text)

# Toggle this based on whether API key is configured
has_ai_features = True

# Main application

def open_ai_chat_window():
    if not has_ai_features:
        tk.messagebox.showinfo("AI Unavailable", "AI features are not enabled. Please check your API key.")
        return

    chat_win = tk.Toplevel(app)
    chat_win.title("Ask Gemini AI - Money Saving Tips")
    chat_win.geometry("500x500")
    chat_win.after_idle(chat_win.grab_set)

    chat_display = tk.Text(chat_win, state="disabled", wrap="word", font=("Helvetica", 12))
    chat_display.pack(fill="both", expand=True, padx=10, pady=10)

    entry_frame = tk.Frame(chat_win)
    entry_frame.pack(fill="x", padx=10, pady=5)

    user_entry = tk.Entry(entry_frame, font=("Helvetica", 12))
    user_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

    def send_to_ai():
        question = user_entry.get().strip()
        if not question:
            return

        chat_display.config(state="normal")
        chat_display.insert("end", f"You: {question}\n")
        chat_display.insert("end", "AI: Thinking...\n")
        chat_display.config(state="disabled")
        chat_display.see("end")
        user_entry.delete(0, "end")
        chat_win.update()

        try:
            response = chat.send_message(question)
            answer = response.text.strip()

            chat_display.config(state="normal")
            chat_display.delete("end-2l", "end-1l")  # Remove "AI: Thinking..."
            chat_display.insert("end", f"AI: {answer}\n\n")
            chat_display.config(state="disabled")
            chat_display.see("end")
        except Exception as e:
            chat_display.config(state="normal")
            chat_display.insert("end", f"AI: Sorry, I couldn't process your request. ({e})\n")
            chat_display.config(state="disabled")
            chat_display.see("end")

    send_btn = tk.Button(entry_frame, text="Ask", font=("Helvetica", 12, "bold"), command=send_to_ai)
    send_btn.pack(side="right")

    user_entry.bind("<Return>", lambda event: send_to_ai())

first_page()

app.mainloop()