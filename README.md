# Veeteq Solar - Solar Company Website

A comprehensive solar company website built with Python Flask, HTML, Tailwind CSS, JavaScript, and MySQL database using XAMPP.

## Features

### Frontend Features
- **Responsive Design**: Modern, mobile-first design using Tailwind CSS
- **Interactive Quote Calculator**: Real-time solar savings calculator
- **Product Catalog**: Filterable solar products with detailed specifications
- **Portfolio Gallery**: Showcase of completed solar installations
- **Contact Forms**: Multiple contact points with form validation
- **Service Pages**: Detailed information about solar services

### Backend Features
- **Flask Web Framework**: Lightweight and flexible Python web framework
- **MySQL Database**: Robust data storage with XAMPP integration
- **Admin Panel**: Complete management system for quotes, customers, and installations
- **Quote Management**: Automated quote calculation and customer management
- **Customer Database**: Comprehensive customer information storage
- **Product Management**: Dynamic product catalog with pricing

### Admin Panel Features
- **Dashboard**: Overview of business metrics and recent activity
- **Customer Management**: View, edit, and manage customer information
- **Quote Management**: Review, approve, and track solar quotes
- **Installation Tracking**: Monitor project progress and status
- **Product Management**: Manage solar products and pricing
- **Reporting**: Business analytics and performance metrics

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Database**: MySQL (via XAMPP)
- **Icons**: Font Awesome
- **Package Manager**: pip (Python packages)

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- XAMPP (for MySQL database)
- Web browser

### 1. Clone/Download the Project
```bash
git clone <repository-url>
cd veeteq-solar
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup XAMPP and MySQL
1. Download and install XAMPP from https://www.apachefriends.org/
2. Start XAMPP Control Panel
3. Start **Apache** and **MySQL** services
4. Open phpMyAdmin (http://localhost/phpmyadmin)
5. The database will be created automatically when you run the application

### 4. Run the Application
```bash
python app.py
```

The application will be available at: **http://localhost:5000**

### 5. Access Admin Panel
- URL: **http://localhost:5000/admin**
- Username: **admin**
- Password: **admin123**

## Project Structure

```
veeteq-solar/
│
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
│
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Homepage
│   ├── services.html     # Services page
│   ├── products.html     # Products catalog
│   ├── quote.html        # Quote calculator
│   ├── contact.html      # Contact page
│   ├── about.html        # About page
│   ├── portfolio.html    # Portfolio gallery
│   ├── admin_login.html  # Admin login
│   ├── admin_dashboard.html # Admin dashboard
│   ├── admin_customers.html # Customer management
│   └── admin_quotes.html # Quote management
│
├── static/               # Static files
│   ├── css/
│   │   └── style.css     # Custom styles
│   ├── js/
│   │   └── main.js       # JavaScript functionality
│   └── uploads/          # File uploads directory
│
└── database/             # Database files (auto-created)
```

## Database Schema

The application automatically creates the following tables:

### customers
- Customer information and contact details
- Addresses and location data
- Creation timestamps

### products
- Solar panels, inverters, batteries, mounting systems
- Pricing, specifications, and warranty information
- Product categories and descriptions

### quotes
- Customer quote requests
- System specifications and calculations
- Cost estimates and savings projections
- Quote status tracking

### installations
- Installation project tracking
- Customer and quote associations
- Project status and completion dates
- Technician assignments

### admin_users
- Admin user authentication
- Role-based access control

## Key Features Explained

### Solar Quote Calculator
- **Input**: Monthly electric bill, roof size, property type
- **Calculations**: System size, installation cost, tax credits, payback period
- **Output**: Detailed savings analysis and system recommendations

### Product Catalog
- **Categories**: Solar panels, inverters, batteries, mounting systems
- **Filtering**: Filter products by category
- **Details**: Specifications, pricing, warranty information

### Admin Dashboard
- **Metrics**: Customer count, quote status, revenue tracking
- **Recent Activity**: Latest quotes and customer interactions
- **Quick Actions**: Direct access to common tasks

## Customization

### Colors and Branding
The application uses custom CSS variables for easy color customization:
- `--solar-blue`: Primary blue color
- `--solar-green`: Success/positive actions
- `--solar-orange`: Call-to-action elements
- `--solar-yellow`: Highlights and accents

### Database Configuration
Update the database configuration in `app.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'veeteq_solar',
    'user': 'root',
    'password': ''  # Your MySQL password
}
```

### Sample Data
The application includes sample data for:
- Solar products with realistic pricing
- Admin user account
- Product categories and specifications

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure XAMPP MySQL is running
   - Check database credentials in `app.py`
   - Verify MySQL service is started in XAMPP

2. **Module Import Errors**
   - Run `pip install -r requirements.txt`
   - Ensure Python 3.7+ is installed
   - Check virtual environment activation

3. **Template Not Found**
   - Verify all templates are in the `templates/` directory
   - Check template names match route handlers
   - Ensure no subfolders in templates directory

4. **Static Files Not Loading**
   - Check static files are in `static/` directory
   - Verify CSS and JS file paths
   - Clear browser cache

### Port Configuration
If port 5000 is in use, modify the last line in `app.py`:
```python
app.run(debug=True, port=5001)  # Change port number
```

## Development

### Adding New Features
1. Create new routes in `app.py`
2. Add corresponding HTML templates
3. Update navigation in `base.html`
4. Add any required database tables

### Database Updates
- Modify the `init_db()` function in `app.py`
- Add new table creation SQL
- Update sample data as needed

## Security Notes

- Change default admin credentials in production
- Use environment variables for sensitive configuration
- Implement proper input validation and sanitization
- Use HTTPS in production environment
- Regular database backups recommended

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the Flask and MySQL documentation
3. Ensure all dependencies are properly installed
4. Verify XAMPP services are running

## License

This project is created for educational and commercial use. Modify and distribute as needed for your solar business requirements.
