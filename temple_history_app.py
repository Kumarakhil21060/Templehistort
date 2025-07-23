import streamlit as st
import sqlite3
import base64
import io
import os
from datetime import datetime
import pandas as pd
from PIL import Image
import tempfile
import requests

# Try to import geolocation packages
try:
    from streamlit_geolocation import streamlit_geolocation
    GEOLOCATION_AVAILABLE = True
except ImportError:
    GEOLOCATION_AVAILABLE = False
    st.warning("streamlit-geolocation not installed. Install with: pip install streamlit-geolocation")

# Page configuration
st.set_page_config(
    page_title="Temple Heritage Hub",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced database setup with location fields
def init_database():
    """Initialize the database with location-enhanced tables"""
    conn = sqlite3.connect('temple_heritage.db')
    c = conn.cursor()
    
    # Enhanced temples table with precise location data
    c.execute('''
        CREATE TABLE IF NOT EXISTS temples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location_address TEXT,
            latitude REAL,
            longitude REAL,
            location_accuracy REAL,
            built_year TEXT,
            deity TEXT,
            architecture_style TEXT,
            description TEXT,
            contributor_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Enhanced media table
    c.execute('''
        CREATE TABLE IF NOT EXISTS temple_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temple_id INTEGER,
            media_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_data BLOB,
            file_size INTEGER,
            description TEXT,
            latitude REAL,
            longitude REAL,
            contributor_name TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (temple_id) REFERENCES temples (id)
        )
    ''')
    
    # Content contributions table for standalone uploads
    c.execute('''
        CREATE TABLE IF NOT EXISTS content_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL,
            description TEXT,
            latitude REAL,
            longitude REAL,
            location_address TEXT,
            contributor_name TEXT,
            file_data BLOB,
            filename TEXT,
            file_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Historical events with location context
    c.execute('''
        CREATE TABLE IF NOT EXISTS historical_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temple_id INTEGER,
            event_date TEXT,
            event_title TEXT,
            event_description TEXT,
            latitude REAL,
            longitude REAL,
            contributor_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (temple_id) REFERENCES temples (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Location handling functions
def get_location_from_ip():
    """Fallback location detection using IP geolocation"""
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'city': data.get('city'),
                'region': data.get('region'),
                'country': data.get('country_name')
            }
    except:
        return None
    return None

def location_input_component():
    """Enhanced location input component with multiple options"""
    st.subheader("📍 Location Information")
    
    # Initialize session state for location
    if 'location_data' not in st.session_state:
        st.session_state.location_data = {
            'latitude': None,
            'longitude': None,
            'address': '',
            'method': None
        }
    
    # Location method selection
    location_method = st.radio(
        "How would you like to set the location?",
        ["📱 Use Device GPS", "🗺️ Manual Entry", "🌐 IP-based Location"],
        horizontal=True
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if location_method == "📱 Use Device GPS":
            st.info("Click 'Get Location' to access your device's GPS. You may need to allow location permissions.")
            
            if GEOLOCATION_AVAILABLE:
                location = streamlit_geolocation()
                
                if location and location.get('latitude'):
                    st.session_state.location_data.update({
                        'latitude': location['latitude'],
                        'longitude': location['longitude'],
                        'method': 'GPS'
                    })
                    st.success(f"✅ Location detected: {location['latitude']:.6f}, {location['longitude']:.6f}")
                    st.write(f"**Accuracy:** {location.get('accuracy', 'Unknown')} meters")
                elif location:
                    st.warning("Location access failed. Please allow location access in your browser settings, reload the page, or enter your location manually.")
            else:
                st.error("GPS location feature requires streamlit-geolocation package. Please install it or use manual entry.")
        
        elif location_method == "🗺️ Manual Entry":
            st.write("**Enter coordinates manually:**")
            
            manual_lat = st.number_input(
                "Latitude", 
                min_value=-90.0, 
                max_value=90.0, 
                value=st.session_state.location_data['latitude'] or 0.0,
                format="%.6f",
                help="Latitude ranges from -90 (South Pole) to +90 (North Pole)"
            )
            
            manual_lon = st.number_input(
                "Longitude", 
                min_value=-180.0, 
                max_value=180.0, 
                value=st.session_state.location_data['longitude'] or 0.0,
                format="%.6f",
                help="Longitude ranges from -180 to +180"
            )
            
            if st.button("📌 Set Location", type="primary"):
                st.session_state.location_data.update({
                    'latitude': manual_lat,
                    'longitude': manual_lon,
                    'method': 'Manual'
                })
                st.success(f"✅ Location set: {manual_lat:.6f}, {manual_lon:.6f}")
        
        elif location_method == "🌐 IP-based Location":
            st.info("Detecting location based on your internet connection...")
            
            if st.button("🔍 Detect IP Location"):
                with st.spinner("Getting location from IP..."):
                    ip_location = get_location_from_ip()
                    
                    if ip_location and ip_location['latitude']:
                        st.session_state.location_data.update({
                            'latitude': ip_location['latitude'],
                            'longitude': ip_location['longitude'],
                            'address': f"{ip_location['city']}, {ip_location['region']}, {ip_location['country']}",
                            'method': 'IP'
                        })
                        st.success(f"✅ Location detected: {ip_location['city']}, {ip_location['country']}")
                        st.write(f"**Coordinates:** {ip_location['latitude']:.6f}, {ip_location['longitude']:.6f}")
                    else:
                        st.error("Could not detect location from IP. Please use manual entry.")
    
    with col2:
        # Display current location
        if st.session_state.location_data['latitude']:
            st.metric("📍 Latitude", f"{st.session_state.location_data['latitude']:.6f}")
            st.metric("📍 Longitude", f"{st.session_state.location_data['longitude']:.6f}")
            
            # Show location on map
            if st.session_state.location_data['latitude'] != 0 or st.session_state.location_data['longitude'] != 0:
                map_data = pd.DataFrame({
                    'latitude': [st.session_state.location_data['latitude']],
                    'longitude': [st.session_state.location_data['longitude']]
                })
                st.map(map_data, zoom=10)
    
    # Address input
    address = st.text_input(
        "📍 Location Description (Optional)",
        value=st.session_state.location_data.get('address', ''),
        placeholder="e.g., Near Main Temple, Temple Street, City"
    )
    st.session_state.location_data['address'] = address
    
    return st.session_state.location_data

def upload_content_interface():
    """Enhanced content upload interface"""
    st.title("🏛️ Contribute to Temple Heritage")
    st.markdown("---")
    
    # Contribution type selection
    contribution_type = st.selectbox(
        "Choose how you'd like to contribute:",
        [
            "📸 Upload Photos/Images",
            "🎵 Share Audio (Prayers, Stories, etc.)",
            "📄 Upload Documents/Texts",
            "🏛️ Add New Temple Information",
            "📚 Share Historical Event/Story"
        ]
    )
    
    with st.form("content_upload_form", clear_on_submit=True):
        # Title/Name field
        title = st.text_input(
            "Title *", 
            placeholder="Give your contribution a descriptive title",
            help="This helps others understand what you're sharing"
        )
        
        # Location component
        location_data = location_input_component()
        
        # Content description
        content_description = st.text_area(
            "Content Description *",
            placeholder="Describe what you're sharing, its significance, historical context, or any interesting details...",
            height=100
        )
        
        # Contributor information
        contributor_name = st.text_input(
            "Your Name (Optional)",
            placeholder="How would you like to be credited?",
            help="Leave blank to contribute anonymously"
        )
        
        # File upload based on contribution type
        uploaded_files = None
        
        if "Photos/Images" in contribution_type:
            uploaded_files = st.file_uploader(
                "Upload Images",
                type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
                accept_multiple_files=True,
                help="You can upload multiple images at once"
            )
        
        elif "Audio" in contribution_type:
            uploaded_files = st.file_uploader(
                "Upload Audio Files",
                type=['mp3', 'wav', 'm4a', 'ogg', 'flac'],
                accept_multiple_files=True,
                help="Share prayers, temple bells, historical narrations, etc."
            )
        
        elif "Documents" in contribution_type:
            uploaded_files = st.file_uploader(
                "Upload Documents",
                type=['pdf', 'doc', 'docx', 'txt', 'rtf'],
                accept_multiple_files=True,
                help="Historical documents, research papers, inscriptions, etc."
            )
        
        # Submit button
        submitted = st.form_submit_button("🚀 Upload Content", type="primary")
        
        if submitted:
            # Validation
            errors = []
            if not title.strip():
                errors.append("Title is required")
            if not content_description.strip():
                errors.append("Content description is required")
            if uploaded_files is None or len(uploaded_files) == 0:
                if "Temple Information" not in contribution_type and "Historical Event" not in contribution_type:
                    errors.append("Please upload at least one file")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Save contribution
                success_count = save_contribution(
                    contribution_type, title, content_description, 
                    location_data, contributor_name, uploaded_files
                )
                
                if success_count > 0:
                    st.success(f"✅ Successfully uploaded {success_count} file(s)! Thank you for your contribution to preserving temple heritage.")
                    st.balloons()
                    
                    # Clear form data
                    st.session_state.location_data = {
                        'latitude': None,
                        'longitude': None,
                        'address': '',
                        'method': None
                    }

def save_contribution(contribution_type, title, description, location_data, contributor_name, uploaded_files):
    """Save contribution to database"""
    conn = sqlite3.connect('temple_heritage.db')
    c = conn.cursor()
    
    success_count = 0
    
    try:
        if "Temple Information" in contribution_type:
            # Save as temple record
            c.execute('''
                INSERT INTO temples (name, location_address, latitude, longitude, 
                                   description, contributor_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                title,
                location_data.get('address', ''),
                location_data.get('latitude'),
                location_data.get('longitude'),
                description,
                contributor_name or 'Anonymous'
            ))
            success_count = 1
            
        elif "Historical Event" in contribution_type:
            # Save as historical event
            c.execute('''
                INSERT INTO historical_events (event_title, event_description, 
                                             latitude, longitude, contributor_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                title,
                description,
                location_data.get('latitude'),
                location_data.get('longitude'),
                contributor_name or 'Anonymous'
            ))
            success_count = 1
            
        else:
            # Save as content contribution with files
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    file_data = uploaded_file.read()
                    file_size = len(file_data)
                    
                    c.execute('''
                        INSERT INTO content_contributions (title, content_type, description,
                                                         latitude, longitude, location_address,
                                                         contributor_name, file_data, filename, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        title,
                        contribution_type,
                        description,
                        location_data.get('latitude'),
                        location_data.get('longitude'),
                        location_data.get('address', ''),
                        contributor_name or 'Anonymous',
                        file_data,
                        uploaded_file.name,
                        file_size
                    ))
                    success_count += 1
        
        conn.commit()
        
    except Exception as e:
        st.error(f"Error saving contribution: {str(e)}")
        success_count = 0
    
    finally:
        conn.close()
    
    return success_count

def browse_contributions():
    """Browse user contributions"""
    st.header("🌟 Community Contributions")
    
    conn = sqlite3.connect('temple_heritage.db')
    
    # Get contributions
    contributions_df = pd.read_sql_query('''
        SELECT title, content_type, description, contributor_name, 
               latitude, longitude, location_address, created_at, filename
        FROM content_contributions 
        ORDER BY created_at DESC
    ''', conn)
    
    temples_df = pd.read_sql_query('''
        SELECT name as title, 'Temple Information' as content_type, 
               description, contributor_name, latitude, longitude, 
               location_address, created_at, NULL as filename
        FROM temples 
        ORDER BY created_at DESC
    ''', conn)
    
    events_df = pd.read_sql_query('''
        SELECT event_title as title, 'Historical Event' as content_type,
               event_description as description, contributor_name,
               latitude, longitude, NULL as location_address, 
               created_at, NULL as filename
        FROM historical_events 
        ORDER BY created_at DESC
    ''', conn)
    
    conn.close()
    
    # Combine all contributions
    all_contributions = pd.concat([contributions_df, temples_df, events_df], ignore_index=True)
    
    if all_contributions.empty:
        st.info("No contributions yet. Be the first to contribute!")
        return
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        content_filter = st.selectbox(
            "Filter by Type",
            ["All"] + list(all_contributions['content_type'].unique())
        )
    
    with col2:
        contributor_filter = st.selectbox(
            "Filter by Contributor", 
            ["All"] + list(all_contributions['contributor_name'].dropna().unique())
        )
    
    with col3:
        location_filter = st.checkbox("Only show contributions with location data")
    
    # Apply filters
    filtered_df = all_contributions.copy()
    
    if content_filter != "All":
        filtered_df = filtered_df[filtered_df['content_type'] == content_filter]
    
    if contributor_filter != "All":
        filtered_df = filtered_df[filtered_df['contributor_name'] == contributor_filter]
    
    if location_filter:
        filtered_df = filtered_df[filtered_df['latitude'].notna()]
    
    # Display contributions
    st.write(f"**Showing {len(filtered_df)} contribution(s)**")
    
    # Map view if location data exists
    map_data = filtered_df[filtered_df['latitude'].notna() & filtered_df['longitude'].notna()]
    if not map_data.empty:
        st.subheader("🗺️ Contribution Locations")
        st.map(map_data[['latitude', 'longitude']], zoom=5)
    
    # List view
    for _, contrib in filtered_df.iterrows():
        with st.expander(f"📋 {contrib['title']} - {contrib['content_type']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Description:** {contrib['description']}")
                st.write(f"**Contributor:** {contrib['contributor_name']}")
                st.write(f"**Uploaded:** {contrib['created_at']}")
                
                if contrib['location_address']:
                    st.write(f"**Location:** {contrib['location_address']}")
                
                if contrib['filename']:
                    st.write(f"**File:** {contrib['filename']}")
            
            with col2:
                if pd.notna(contrib['latitude']) and pd.notna(contrib['longitude']):
                    st.metric("📍 Latitude", f"{contrib['latitude']:.6f}")
                    st.metric("📍 Longitude", f"{contrib['longitude']:.6f}")

# Main application
def main():
    # Initialize database
    init_database()
    
    # Sidebar navigation
    st.sidebar.title("🏛️ Temple Heritage Hub")
    st.sidebar.markdown("---")
    
    page = st.sidebar.selectbox("Navigate", [
        "🏠 Home",
        "📤 Upload Content", 
        "🗂️ Browse Temples",
        "🌟 Community Contributions",
        "📊 Heritage Statistics",
        "🗺️ Heritage Map"
    ])
    
    if page == "🏠 Home":
        show_enhanced_home()
    elif page == "📤 Upload Content":
        upload_content_interface()
    elif page == "🗂️ Browse Temples":
        view_temples()
    elif page == "🌟 Community Contributions":
        browse_contributions()
    elif page == "📊 Heritage Statistics":
        show_heritage_statistics()
    elif page == "🗺️ Heritage Map":
        show_heritage_map()

def show_enhanced_home():
    """Enhanced home page"""
    st.title("🏛️ Temple Heritage Hub")
    st.markdown("### *Preserving Sacred Stories Through Community Collaboration*")
    st.markdown("---")
    
    # Welcome message
    st.markdown("""
    **Welcome to Temple Heritage Hub** - a digital sanctuary where communities come together to preserve, 
    share, and celebrate the rich history of temples and sacred places. Your contributions help build 
    a comprehensive archive for future generations.
    """)
    
    # Quick action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Contribute Content", type="primary", use_container_width=True):
            st.switch_page("Upload Content")
    
    with col2:
        if st.button("🗂️ Explore Temples", use_container_width=True):
            st.switch_page("Browse Temples")
    
    with col3:
        if st.button("🗺️ Heritage Map", use_container_width=True):
            st.switch_page("Heritage Map")
    
    # Statistics overview
    conn = sqlite3.connect('temple_heritage.db')
    
    temple_count = pd.read_sql_query("SELECT COUNT(*) as count FROM temples", conn)['count'][0]
    contribution_count = pd.read_sql_query("SELECT COUNT(*) as count FROM content_contributions", conn)['count'][0]
    event_count = pd.read_sql_query("SELECT COUNT(*) as count FROM historical_events", conn)['count'][0]
    
    conn.close()
    
    st.markdown("### 📊 Community Impact")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏛️ Temples Documented", temple_count)
    with col2:
        st.metric("📁 Content Contributions", contribution_count)
    with col3:
        st.metric("📚 Historical Events", event_count)
    with col4:
        st.metric("🌍 Total Heritage Items", temple_count + contribution_count + event_count)

def show_heritage_map():
    """Display all heritage locations on a map"""
    st.header("🗺️ Heritage Locations Map")
    
    conn = sqlite3.connect('temple_heritage.db')
    
    # Get all locations
    locations_query = '''
        SELECT name as title, 'Temple' as type, latitude, longitude, location_address 
        FROM temples WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        UNION ALL
        SELECT title, content_type as type, latitude, longitude, location_address
        FROM content_contributions WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        UNION ALL
        SELECT event_title as title, 'Historical Event' as type, latitude, longitude, NULL as location_address
        FROM historical_events WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    '''
    
    locations_df = pd.read_sql_query(locations_query, conn)
    conn.close()
    
    if locations_df.empty:
        st.info("No locations with coordinates found yet. Start contributing to see them on the map!")
        return
    
    # Display map
    st.write(f"**Showing {len(locations_df)} heritage location(s)**")
    
    # Color coding by type
    type_colors = {
        'Temple': '#FF0000',
        'Historical Event': '#00FF00', 
        'Photos/Images': '#0000FF',
        'Audio': '#FF00FF',
        'Documents': '#FFFF00'
    }
    
    st.map(locations_df[['latitude', 'longitude']], zoom=5)
    
    # Legend
    st.markdown("### 🎨 Map Legend")
    for item_type, color in type_colors.items():
        if item_type in locations_df['type'].values:
            st.markdown(f"🔴 **{item_type}**")

def show_heritage_statistics():
    """Enhanced statistics dashboard"""
    st.header("📊 Heritage Statistics Dashboard")
    
    conn = sqlite3.connect('temple_heritage.db')
    
    # Various statistics queries
    temple_stats = pd.read_sql_query('''
        SELECT 
            COUNT(*) as total_temples,
            COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as temples_with_location,
            COUNT(CASE WHEN contributor_name != 'Anonymous' THEN 1 END) as temples_with_named_contributors
        FROM temples
    ''', conn)
    
    content_stats = pd.read_sql_query('''
        SELECT 
            content_type,
            COUNT(*) as count,
            SUM(file_size) as total_size
        FROM content_contributions 
        GROUP BY content_type
    ''', conn)
    
    monthly_contributions = pd.read_sql_query('''
        SELECT 
            strftime('%Y-%m', created_at) as month,
            COUNT(*) as contributions
        FROM content_contributions 
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month DESC
        LIMIT 12
    ''', conn)
    
    conn.close()
    
    # Display statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Temples", temple_stats['total_temples'].iloc[0])
    with col2:
        st.metric("Temples with GPS", temple_stats['temples_with_location'].iloc[0])
    with col3:
        st.metric("Named Contributors", temple_stats['temples_with_named_contributors'].iloc[0])
    
    # Content type distribution
    if not content_stats.empty:
        st.subheader("📁 Content Type Distribution")
        st.bar_chart(content_stats.set_index('content_type')['count'])
    
    # Monthly contribution trends
    if not monthly_contributions.empty:
        st.subheader("📈 Monthly Contribution Trends")
        st.line_chart(monthly_contributions.set_index('month')['contributions'])

# Enhanced temple viewing with location integration
def view_temples():
    """Enhanced temple viewing with location features"""
    st.header("🏛️ Temple Heritage Collection")
    
    conn = sqlite3.connect('temple_heritage.db')
    temples_df = pd.read_sql_query('''
        SELECT *, 
               CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL 
                    THEN 'Yes' ELSE 'No' END as has_location
        FROM temples 
        ORDER BY created_at DESC
    ''', conn)
    conn.close()
    
    if temples_df.empty:
        st.info("No temples found. Start contributing to build our heritage collection!")
        return
    
    # Enhanced filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search temples", placeholder="Search by name, location, or deity...")
    
    with col2:
        location_filter = st.selectbox("Location Data", ["All", "With GPS coordinates", "Without GPS coordinates"])
    
    with col3:
        architecture_filter = st.selectbox("Architecture Style", ["All"] + list(temples_df['architecture_style'].dropna().unique()))
    
    # Apply filters
    filtered_df = temples_df.copy()
    
    if search_term:
        mask = filtered_df.apply(lambda x: x.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)
        filtered_df = filtered_df[mask]
    
    if location_filter == "With GPS coordinates":
        filtered_df = filtered_df[filtered_df['has_location'] == 'Yes']
    elif location_filter == "Without GPS coordinates":
        filtered_df = filtered_df[filtered_df['has_location'] == 'No']
    
    if architecture_filter != "All":
        filtered_df = filtered_df[filtered_df['architecture_style'] == architecture_filter]
    
    # Display results
    st.write(f"**Found {len(filtered_df)} temple(s)**")
    
    # Map view for temples with coordinates
    temples_with_coords = filtered_df[filtered_df['has_location'] == 'Yes']
    if not temples_with_coords.empty:
        st.subheader("🗺️ Temple Locations")
        st.map(temples_with_coords[['latitude', 'longitude']], zoom=5)
    
    # Temple cards
    for _, temple in filtered_df.iterrows():
        with st.expander(f"🏛️ {temple['name']} - {temple['location_address'] or 'Location not specified'}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if temple['deity']:
                    st.write(f"**Deity:** {temple['deity']}")
                if temple['built_year']:
                    st.write(f"**Built:** {temple['built_year']}")
                if temple['architecture_style']:
                    st.write(f"**Architecture:** {temple['architecture_style']}")
                st.write(f"**Description:** {temple['description']}")
                st.write(f"**Contributor:** {temple['contributor_name']}")
                st.write(f"**Added:** {temple['created_at']}")
            
            with col2:
                if temple['has_location'] == 'Yes':
                    st.metric("📍 Latitude", f"{temple['latitude']:.6f}")
                    st.metric("📍 Longitude", f"{temple['longitude']:.6f}")
                else:
                    st.info("No GPS coordinates available")

if __name__ == "__main__":
    main()
