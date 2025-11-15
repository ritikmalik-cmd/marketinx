import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os

# Zoho CRM API details - Load from Streamlit secrets
try:
    ZOHO_CLIENT_ID = st.secrets["ZOHO_CLIENT_ID"]
    ZOHO_CLIENT_SECRET = st.secrets["ZOHO_CLIENT_SECRET"]
    ZOHO_REFRESH_TOKEN = st.secrets["ZOHO_REFRESH_TOKEN"]
    ZOHO_REDIRECT_URI = st.secrets.get("ZOHO_REDIRECT_URI", "http://localhost:7860")
except KeyError:
    # Fallback for local development (will fail gracefully if secrets not set)
    ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
    ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
    ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN", "")
    ZOHO_REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:7860")

ZOHO_API_BASE_URL = "https://www.zohoapis.com/crm/v2"

# Cache the token for 30 minutes
@st.cache_data(ttl=1800)
def get_access_token_cached():
    """Get access token using refresh token (cached)"""
    return get_access_token()

# Cache all leads for 1 hour
@st.cache_data(ttl=3600)
def fetch_all_leads_cached(dummy_param=None):
    """Fetch all leads from Zoho CRM with pagination (cached)"""
    token = get_access_token_cached()
    return fetch_all_leads(token)

def get_access_token():
    """Get access token using refresh token"""
    try:
        url = "https://accounts.zoho.com/oauth/v2/token"
        payload = {
            "client_id": ZOHO_CLIENT_ID,
            "client_secret": ZOHO_CLIENT_SECRET,
            "refresh_token": ZOHO_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(url, data=payload)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data.get('access_token')
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error getting access token: {e}")
        return None

def fetch_all_leads(access_token):
    """Fetch all leads from Zoho CRM with pagination - optimized"""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{ZOHO_API_BASE_URL}/Leads"
        all_leads = []
        page = 1
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while True:
            params = {
                "per_page": 200,
                "page": page,
                # Only fetch the fields we need to reduce payload
                "fields": "id,First_Name,Last_Name,Email,Phone,Company,Owner,Lead_Status,Lead_Source,Created_Time,Rating"
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                st.error(f"API Error: {response.status_code} - {response.text}")
                break
            
            leads_data = response.json()
            leads = leads_data.get('data', [])
            
            if not leads:
                break
            
            all_leads.extend(leads)
            
            # Update progress
            status_text.text(f"Fetched {len(all_leads)} leads...")
            progress_bar.progress(min(len(all_leads) / 30000, 1.0))
            
            # Check if there are more pages
            info = leads_data.get('info', {})
            has_more = info.get('more_records', False)
            if not has_more:
                break
            
            page += 1
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        return all_leads
    
    except Exception as e:
        st.error(f"Error fetching leads: {e}")
        return []

def fetch_leads_by_date_range_client(all_leads, start_date, end_date):
    """Filter leads by date range (client-side, from cached data)"""
    filtered_leads = []
    
    for lead in all_leads:
        created_time_str = lead.get('Created_Time', '')
        if created_time_str:
            try:
                # Parse the ISO 8601 datetime
                created_time = datetime.fromisoformat(created_time_str.replace('Z', '+00:00'))
                # Convert to date for comparison
                created_date = created_time.date() if hasattr(created_time, 'date') else created_time
                
                if start_date <= created_date <= end_date:
                    filtered_leads.append(lead)
            except (ValueError, AttributeError):
                # If we can't parse the date, include the lead
                filtered_leads.append(lead)
    
    return filtered_leads

# --- NEW FUNCTION FOR MESSAGE GENERATION ---
def create_message_column(df):
    """Generates a formatted text message for each lead."""
    def generate_message(row):
        # Format the lead data into a clean, copy-pastable text message
        message = (
            f"⚡️ *NEW LEAD ASSIGNED!* ⚡️\n\n"
            f"👤 *Name:* {row['Full Name']}\n"
            f"🏢 *Company:* {row['Company']}\n"
            f"📞 *Phone:* {row['Phone']}\n"
            f"📧 *Email:* {row['Email']}\n"
            f"🌐 *Source:* {row['Lead Source']}\n\n"
            f"✅ *Action: Contact Immediately!* (Owner: {row['Lead Owner']})"
        )
        return message
    
    # Apply the function to each row
    df['Shareable Message'] = df.apply(generate_message, axis=1)
    return df
# -------------------------------------------

def process_leads_data(leads):
    """Process leads data into a DataFrame"""
    processed_leads = []
    
    for lead in leads:
        # Extract Lead Owner from 'Owner' field (Zoho API field)
        owner_obj = lead.get('Owner')
        if isinstance(owner_obj, dict):
            # Owner field contains name, id, and email
            lead_owner_name = owner_obj.get('name', 'Unassigned')
        elif isinstance(owner_obj, str):
            lead_owner_name = owner_obj if owner_obj else 'Unassigned'
        else:
            lead_owner_name = 'Unassigned'
        
        processed_leads.append({
            'ID': lead.get('id', 'N/A'),
            'First Name': lead.get('First_Name', ''),
            'Last Name': lead.get('Last_Name', ''),
            'Full Name': f"{lead.get('First_Name', '')} {lead.get('Last_Name', '')}".strip(),
            'Email': lead.get('Email', 'N/A'),
            'Phone': lead.get('Phone', 'N/A'),
            'Company': lead.get('Company', 'N/A'),
            'Lead Owner': lead_owner_name,
            'Lead Status': lead.get('Lead_Status', 'No Status'),
            'Lead Source': lead.get('Lead_Source', 'No Source'),
            'Created Time': lead.get('Created_Time', 'N/A'),
            'Rating': lead.get('Rating', 'N/A')
        })
    
    return pd.DataFrame(processed_leads)

def get_most_common(x):
    """Get the most common value in a series, handling empty results"""
    vc = x.value_counts()
    return vc.index[0] if len(vc) > 0 else 'N/A'

def create_dashboard():
    """Create the marketing dashboard"""
    st.set_page_config(page_title="Marketing Dashboard", layout="wide", initial_sidebar_state="expanded")
    
    # Custom styling
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .title {
        font-size: 2.5em;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.markdown('<div class="title">📊 Marketing Dashboard</div>', unsafe_allow_html=True)
    
    # Sidebar for filters
    st.sidebar.markdown("## 🎯 Filters")
    
    # Date range filter (Updated to include "Today")
    st.sidebar.subheader("📅 Date Range")
    date_range_option = st.sidebar.radio("Select date range:", ["Today", "This Week", "All Time", "Last 30 Days", "Last 90 Days", "Custom"], index=0)
    
    today = datetime.now().date()
    
    if date_range_option == "Today":
        start_date = today
        end_date = today
    elif date_range_option == "This Week":
        # Get Monday of this week
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range_option == "All Time":
        start_date = datetime(2020, 1, 1).date()
        end_date = today
    elif date_range_option == "Last 30 Days":
        end_date = today
        start_date = (today - timedelta(days=30))
    elif date_range_option == "Last 90 Days":
        end_date = today
        start_date = (today - timedelta(days=90))
    else:  # Custom
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Start Date", today - timedelta(days=90))
        with col2:
            end_date = st.date_input("End Date", today)
    
    # Get access token and fetch leads
    with st.spinner("Loading data from Zoho CRM..."):
        # Fetch all leads using cache
        all_leads = fetch_all_leads_cached()
        
        if not all_leads:
            st.error("No leads found")
            return
        
        # Filter by date range
        filtered_leads = fetch_leads_by_date_range_client(all_leads, start_date, end_date)
        
        if not filtered_leads:
            st.error("No leads found for the selected date range")
            return
        
        df = process_leads_data(filtered_leads)
        
        # --- APPLY NEW MESSAGE COLUMN ---
        df = create_message_column(df)
        # --------------------------------
        
        st.sidebar.success(f"✅ Fetched {len(df)} leads from {start_date} to {end_date}\n(Total in DB: {len(all_leads)} leads)")
    
    # Display last updated time
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Leads: {len(df)}")
    
    
    # --- NEW DEDICATED SECTION FOR TODAY'S LEADS AND MESSAGE ---
    st.header("📲 Fresh Leads for Today's Follow-up")
    st.info("The table below shows all leads created *today* for quick copying and sharing. If the table is empty, no new leads have been created today.")
    
    # Filter the main DataFrame to only show leads assigned to the target owner
    # This filter ensures you only see the leads assigned to the user you need to update.
    target_owner_name = st.text_input("Filter Leads by Assigned Owner Name:", value="New Admin Name") 
    
    today_leads_df = df[df['Created Time'].str.contains(str(today))] # Filter to only show today's leads
    
    if target_owner_name:
        # Filter by the target owner
        today_leads_df = today_leads_df[today_leads_df['Lead Owner'].str.contains(target_owner_name, case=False, na=False)]
    
    if today_leads_df.empty:
        st.warning(f"No new leads found today assigned to '{target_owner_name}'.")
    else:
        st.subheader(f"{len(today_leads_df)} New Leads for '{target_owner_name}' Today")
        
        # Display the table with the new 'Shareable Message' column
        st.dataframe(
            today_leads_df[['Full Name', 'Lead Owner', 'Shareable Message']],
            use_container_width=True,
            hide_index=True,
            column_config={
                'Full Name': st.column_config.TextColumn('Lead Name', width='small'),
                'Lead Owner': st.column_config.TextColumn('Assigned To', width='small'),
                # Configure the message column to display as a long text box for easy copying
                'Shareable Message': st.column_config.TextColumn('SMS/WhatsApp Message (Copy)', width='large')
            }
        )
    
    st.divider()
    # -------------------------------------------------------------
    
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Leads", len(df), delta=None)
    
    with col2:
        st.metric("Lead Owners", df['Lead Owner'].nunique(), delta=None)
    
    with col3:
        st.metric("Lead Sources", df['Lead Source'].nunique(), delta=None)
    
    with col4:
        st.metric("Lead Statuses", df['Lead Status'].nunique(), delta=None)
    
    st.divider()
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "By Lead Owner", "By Lead Status", "By Lead Source", "Data Table"])
    
    with tab1:
        st.subheader("📈 Dashboard Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Lead Owner Distribution
            lead_owner_counts = df['Lead Owner'].value_counts().reset_index()
            lead_owner_counts.columns = ['Lead Owner', 'Count']
            
            fig_owner = px.pie(
                lead_owner_counts,
                values='Count',
                names='Lead Owner',
                title='Leads Distribution by Owner',
                template='plotly_white',
                hole=0.4
            )
            fig_owner.update_traces(textposition='inside', textinfo='label+percent')
            st.plotly_chart(fig_owner, use_container_width=True)
        
        with col2:
            # Lead Status Distribution
            lead_status_counts = df['Lead Status'].value_counts().reset_index()
            lead_status_counts.columns = ['Lead Status', 'Count']
            
            fig_status = px.pie(
                lead_status_counts,
                values='Count',
                names='Lead Status',
                title='Leads Distribution by Status',
                template='plotly_white',
                hole=0.4
            )
            fig_status.update_traces(textposition='inside', textinfo='label+percent')
            st.plotly_chart(fig_status, use_container_width=True)
        
        # Lead Source Distribution
        lead_source_counts = df['Lead Source'].value_counts().reset_index()
        lead_source_counts.columns = ['Lead Source', 'Count']
        
        fig_source = px.bar(
            lead_source_counts,
            x='Lead Source',
            y='Count',
            title='Leads Distribution by Source',
            template='plotly_white',
            color='Count',
            color_continuous_scale='Blues'
        )
        fig_source.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig_source, use_container_width=True)
    
    with tab2:
        st.subheader("👤 Leads by Lead Owner - Status Breakdown")
        
        # Add Lead Source filter
        source_filter = st.multiselect("Filter by Lead Source", df['Lead Source'].unique(), key="tab2_source_filter")
        
        # Apply source filter
        tab2_df = df.copy()
        if source_filter:
            tab2_df = tab2_df[tab2_df['Lead Source'].isin(source_filter)]
        
        # Lead Owner statistics with detailed status breakdown
        lead_owner_stats = tab2_df.groupby('Lead Owner').agg({
            'ID': 'count'
        }).rename(columns={'ID': 'Total Leads'}).reset_index()
        
        lead_owner_stats = lead_owner_stats.sort_values('Total Leads', ascending=False)
        
        # Bar chart
        fig = px.bar(
            lead_owner_stats,
            x='Lead Owner',
            y='Total Leads',
            title='Leads Count by Owner',
            template='plotly_white',
            color='Total Leads',
            color_continuous_scale='Viridis',
            text='Total Leads'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed status breakdown for each Lead Owner
        st.subheader("Detailed Status Breakdown by Lead Owner")
        
        for owner in lead_owner_stats['Lead Owner'].values:
            owner_data = tab2_df[tab2_df['Lead Owner'] == owner]
            status_counts = owner_data['Lead Status'].value_counts().to_dict()
            
            # Create columns for display
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**{owner}** (Total: {len(owner_data)})")
            
            # Display status breakdown as a nice formatted text
            status_text = " | ".join([f"{status}: **{count}**" for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True)])
            st.markdown(status_text, unsafe_allow_html=True)
            
            st.divider()
    
    with tab3:
        st.subheader("📋 Leads by Status")
        
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            owner_filter = st.multiselect("Filter by Lead Owner", df['Lead Owner'].unique(), key="tab3_owner_filter")
        with col2:
            source_filter_tab3 = st.multiselect("Filter by Lead Source", df['Lead Source'].unique(), key="tab3_source_filter")
        
        # Apply owner filter
        tab3_df = df.copy()
        if owner_filter:
            tab3_df = tab3_df[tab3_df['Lead Owner'].isin(owner_filter)]
        if source_filter_tab3:
            tab3_df = tab3_df[tab3_df['Lead Source'].isin(source_filter_tab3)]
        
        # Lead Status statistics
        lead_status_stats = tab3_df.groupby('Lead Status').agg({
            'ID': 'count',
            'Lead Owner': get_most_common,
            'Lead Source': get_most_common
        }).rename(columns={'ID': 'Total Leads'}).reset_index()
        
        lead_status_stats = lead_status_stats.sort_values('Total Leads', ascending=False)
        
        # Bar chart
        fig = px.bar(
            lead_status_stats,
            x='Lead Status',
            y='Total Leads',
            title='Leads Count by Status',
            template='plotly_white',
            color='Total Leads',
            color_continuous_scale='RdYlGn',
            text='Total Leads'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Table view
        st.dataframe(
            lead_status_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Lead Status': st.column_config.TextColumn('Lead Status'),
                'Total Leads': st.column_config.NumberColumn('Total Leads'),
                'Lead Owner': st.column_config.TextColumn('Most Common Owner'),
                'Lead Source': st.column_config.TextColumn('Most Common Source')
            }
        )
    
    with tab4:
        st.subheader("🌐 Leads by Source")
        
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            owner_filter_tab4 = st.multiselect("Filter by Lead Owner", df['Lead Owner'].unique(), key="tab4_owner_filter")
        with col2:
            status_filter_tab4 = st.multiselect("Filter by Lead Status", df['Lead Status'].unique(), key="tab4_status_filter")
        
        # Apply filters
        tab4_df = df.copy()
        if owner_filter_tab4:
            tab4_df = tab4_df[tab4_df['Lead Owner'].isin(owner_filter_tab4)]
        if status_filter_tab4:
            tab4_df = tab4_df[tab4_df['Lead Status'].isin(status_filter_tab4)]
        
        # Lead Source statistics
        lead_source_stats = tab4_df.groupby('Lead Source').agg({
            'ID': 'count',
            'Lead Owner': get_most_common,
            'Lead Status': get_most_common
        }).rename(columns={'ID': 'Total Leads'}).reset_index()
        
        lead_source_stats = lead_source_stats.sort_values('Total Leads', ascending=False)
        
        # Bar chart
        fig = px.bar(
            lead_source_stats,
            x='Lead Source',
            y='Total Leads',
            title='Leads Count by Source',
            template='plotly_white',
            color='Total Leads',
            color_continuous_scale='Turbo',
            text='Total Leads'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Table view
        st.dataframe(
            lead_source_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Lead Source': st.column_config.TextColumn('Lead Source'),
                'Total Leads': st.column_config.NumberColumn('Total Leads'),
                'Lead Owner': st.column_config.TextColumn('Most Common Owner'),
                'Lead Status': st.column_config.TextColumn('Most Common Status')
            }
        )
    
    with tab5:
        st.subheader("📊 Complete Leads Data")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_owner = st.multiselect("Filter by Lead Owner", df['Lead Owner'].unique())
        
        with col2:
            selected_status = st.multiselect("Filter by Status", df['Lead Status'].unique())
        
        with col3:
            selected_source = st.multiselect("Filter by Source", df['Lead Source'].unique())
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_owner:
            filtered_df = filtered_df[filtered_df['Lead Owner'].isin(selected_owner)]
        
        if selected_status:
            filtered_df = filtered_df[filtered_df['Lead Status'].isin(selected_status)]
        
        if selected_source:
            filtered_df = filtered_df[filtered_df['Lead Source'].isin(selected_source)]
        
        st.dataframe(
            filtered_df[['Full Name', 'Email', 'Company', 'Lead Owner', 'Lead Status', 'Lead Source', 'Created Time']],
            use_container_width=True,
            hide_index=True,
            column_config={
                'Full Name': st.column_config.TextColumn('Full Name', width='medium'),
                'Email': st.column_config.TextColumn('Email', width='medium'),
                'Company': st.column_config.TextColumn('Company', width='medium'),
                'Lead Owner': st.column_config.TextColumn('Lead Owner', width='medium'),
                'Lead Status': st.column_config.TextColumn('Status', width='small'),
                'Lead Source': st.column_config.TextColumn('Source', width='small'),
                'Created Time': st.column_config.TextColumn('Created', width='medium')
            }
        )
        
        st.info(f"Showing {len(filtered_df)} of {len(df)} leads")

if __name__ == "__main__":
    create_dashboard()
