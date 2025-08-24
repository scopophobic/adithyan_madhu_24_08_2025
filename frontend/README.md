# 🍽️ Store Monitoring Frontend

A simple HTML/CSS/JavaScript frontend for the Store Monitoring API.

## 🚀 How to Use

### 1. Start the Backend Server
```bash
cd ..  # Go back to project root
uvicorn app.main:app --reload
```

### 2. Access the Frontend
Open your browser and go to: **http://localhost:8000/static/index.html**

## 📱 Features

### 🏠 **Main Dashboard**
- View all available reports
- See report status (Complete ✅, Running ⏳, Failed ❌)
- Click on any completed report to view restaurants

### 🍽️ **Restaurant List**
- Shows all restaurants in the selected report
- Color-coded performance indicators:
  - 🟢 **Excellent** (≥95% uptime)
  - 🟡 **Good** (90-94% uptime)  
  - 🟠 **Fair** (80-89% uptime)
  - 🔴 **Poor** (70-79% uptime)
  - ⚫ **Critical** (<70% uptime)
- Quick uptime overview (Hour/Day/Week)

### 🏪 **Restaurant Details**
- Detailed uptime breakdown
- Performance status badge
- Time period analysis (Last Hour/Day/Week)
- Business hours summary

## 🎯 User Flow

1. **View Reports** → Select a completed report
2. **Browse Restaurants** → Click on any restaurant  
3. **View Details** → See detailed uptime information
4. **Navigate Back** → Use back buttons to return

## 🛠️ Technical Details

- **Pure HTML/CSS/JavaScript** - No frameworks needed
- **Responsive Design** - Works on desktop and mobile
- **Error Handling** - Shows user-friendly error messages
- **Loading States** - Visual feedback during API calls

## 🔧 API Integration

The frontend connects to these API endpoints:
- `GET /reports` - List all reports
- `GET /restaurants?report_id=xxx` - Get restaurants in report
- `GET /restaurant/{store_id}?report_id=xxx` - Get restaurant details

## 🎨 Styling

- Clean, minimal design
- Color-coded performance indicators
- Responsive grid layouts
- Hover effects for better UX

## 🚨 Troubleshooting

### No Data Showing?
1. Make sure backend is running on `localhost:8000`
2. Check if data is ingested: `GET /stats`
3. Generate a report if none exist: `POST /trigger_report`

### CORS Errors?
- Backend includes CORS middleware for local development
- Check browser console for specific errors

### API Errors?
- Open browser console (F12) to see detailed error messages
- Check backend server logs

## 📂 File Structure

```
frontend/
├── index.html      # Main HTML structure
├── style.css       # Simple, clean styling  
├── script.js       # API integration & interactions
└── README.md       # This file
```

**Perfect for viewing your restaurant monitoring data! 🎉**
