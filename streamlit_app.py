"""Streamlit UI for the Research Assistant API."""

import streamlit as st
import requests
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-badge {
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-completed { background: #10b981; color: white; }
    .status-awaiting { background: #f59e0b; color: white; }
    .status-researching { background: #3b82f6; color: white; }
    .status-pending { background: #6b7280; color: white; }
    .status-failed { background: #ef4444; color: white; }
    .result-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .critique-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .source-link {
        color: #667eea;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)


def get_status_color(status: str) -> str:
    """Get CSS class for status badge."""
    status_colors = {
        "completed": "status-completed",
        "awaiting_approval": "status-awaiting",
        "researching": "status-researching",
        "pending": "status-pending",
        "failed": "status-failed",
        "rejected": "status-failed",
    }
    return status_colors.get(status, "status-pending")


def display_status_badge(status: str):
    """Display a styled status badge."""
    color_map = {
        "completed": "🟢",
        "awaiting_approval": "🟡",
        "researching": "🔵",
        "pending": "⚪",
        "failed": "🔴",
        "rejected": "🔴",
    }
    emoji = color_map.get(status, "⚪")
    st.markdown(f"**Status:** {emoji} `{status}`")


def start_research(query: str, thread_id: Optional[str], enable_hitl: bool) -> dict:
    """Call the API to start a research session."""
    payload = {
        "query": query,
        "enable_hitl": enable_hitl
    }
    if thread_id:
        payload["thread_id"] = thread_id
    
    response = requests.post(f"{API_BASE_URL}/research", json=payload)
    return response.json()


def get_session(thread_id: str) -> dict:
    """Get the current state of a research session."""
    response = requests.get(f"{API_BASE_URL}/research/{thread_id}")
    if response.status_code == 404:
        return None
    return response.json()


def approve_session(thread_id: str, approved: bool, feedback: Optional[str]) -> dict:
    """Approve or reject a research session."""
    payload = {
        "approved": approved,
    }
    if feedback:
        payload["feedback"] = feedback
    
    response = requests.post(f"{API_BASE_URL}/research/{thread_id}/approve", json=payload)
    return response.json()


def get_checkpoints(thread_id: str) -> dict:
    """Get checkpoints for a session."""
    response = requests.get(f"{API_BASE_URL}/research/{thread_id}/checkpoints")
    return response.json()


def get_all_sessions() -> dict:
    """Get all research sessions."""
    response = requests.get(f"{API_BASE_URL}/research/sessions/all")
    return response.json()


def check_api_health() -> bool:
    """Check if the API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


# Main UI
st.markdown('<h1 class="main-header">🔬 Research Assistant</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    # API Health Check
    if check_api_health():
        st.success("✅ API Connected")
    else:
        st.error("❌ API Offline")
        st.info("Start the FastAPI server:\n```\nuvicorn app.main:app --reload\n```")
    
    st.divider()
    
    # Navigation
    page = st.radio(
        "Navigate",
        ["🚀 New Research", "📚 All Sessions", "📋 Check Session", "✅ Approve Session", "🕐 Time Travel"],
        label_visibility="collapsed"
    )

# Main content area
if page == "🚀 New Research":
    st.markdown("## 🚀 Start New Research")
    st.markdown("Enter your research query and let the AI investigate it for you.")
    
    with st.form("research_form"):
        query = st.text_area(
            "Research Query",
            placeholder="What are the latest advancements in LangGraph?",
            height=100,
            help="Enter a detailed research question"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            thread_id = st.text_input(
                "Thread ID (optional)",
                placeholder="Leave empty for auto-generated",
                help="Custom thread ID for session persistence"
            )
        with col2:
            enable_hitl = st.checkbox(
                "Enable Human-in-the-Loop",
                value=True,
                help="Pause for human approval before final synthesis"
            )
        
        submitted = st.form_submit_button("🔍 Start Research", use_container_width=True)
        
        if submitted:
            if not query or len(query) < 3:
                st.error("Please enter a research query (at least 3 characters)")
            else:
                with st.spinner("🔬 Initiating research..."):
                    try:
                        result = start_research(query, thread_id if thread_id else None, enable_hitl)
                        
                        # Store result in session state
                        st.session_state['last_thread_id'] = result.get('thread_id')
                        st.session_state['last_result'] = result
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # Display stored result (persists after form submission)
    if 'last_result' in st.session_state:
        result = st.session_state['last_result']
        
        st.divider()
        
        # Status header
        status = result.get('status', 'unknown')
        if status == 'completed':
            st.success(f"✅ {result.get('message', 'Research completed')}")
        elif status == 'awaiting_approval':
            st.warning(f"🛑 {result.get('message', 'Awaiting approval')}")
        else:
            st.info(f"ℹ️ {result.get('message', 'Research in progress')}")
        
        # Display result metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Thread ID", result.get('thread_id', 'N/A'))
        with col2:
            display_status_badge(status)
        with col3:
            st.metric("Revisions", result.get('revision_count', 0))
        
        # Show gathered results if any
        if result.get('gathered_results'):
            st.markdown("### 📚 Research Results")
            for item in result['gathered_results']:
                with st.expander(f"Step {item['step_id']}: {item['query'][:50]}...", expanded=True):
                    for i, res in enumerate(item['results']):
                        st.markdown(f"**Finding {i+1}:** {res}")
                    if item['sources']:
                        st.markdown("**Sources:**")
                        for src in item['sources']:
                            st.markdown(f"- 🔗 [{src}]({src})")
        
        # Show critique if available
        if result.get('critique'):
            st.markdown("### 📝 Critique Analysis")
            critique = result['critique']
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Score", f"{critique['score']:.0%}")
            with col2:
                st.progress(critique['score'])
            
            st.markdown(f"**Feedback:** {critique['feedback']}")
            
            if critique.get('should_refine'):
                st.warning("⚠️ Further refinement recommended")
            else:
                st.success("✅ Quality threshold met")
            
            if critique.get('suggestions'):
                st.markdown("**Suggestions:**")
                for sug in critique['suggestions']:
                    st.markdown(f"- 💡 {sug}")
        
        # Show final response if completed
        if result.get('final_response'):
            st.markdown("### 🎯 Final Response")
            st.markdown(result['final_response'])
            
            # Clear button to start fresh
            if st.button("🔄 Start New Research", use_container_width=True):
                del st.session_state['last_result']
                st.rerun()
        
        # Show APPROVE button if awaiting approval
        elif status == 'awaiting_approval':
            st.markdown("---")
            st.markdown("### ✅ Human Approval Required")
            st.info("The research is ready for your review. Approve to generate the final synthesis.")
            
            # Feedback input (outside form for immediate interaction)
            feedback = st.text_area(
                "Feedback (optional)",
                placeholder="Add any feedback to incorporate in the final synthesis...",
                key="approval_feedback"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve & Continue", type="primary", use_container_width=True):
                    with st.spinner("🔬 Generating final synthesis..."):
                        try:
                            approval_result = approve_session(
                                result.get('thread_id'),
                                True,
                                feedback if feedback else None
                            )
                            
                            if 'detail' in approval_result:
                                st.error(f"❌ {approval_result['detail']}")
                            else:
                                # Update stored result with final response
                                st.session_state['last_result'] = approval_result
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            
            with col2:
                if st.button("❌ Reject", use_container_width=True):
                    try:
                        approval_result = approve_session(
                            result.get('thread_id'),
                            False,
                            None
                        )
                        st.session_state['last_result'] = approval_result
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")


elif page == "📚 All Sessions":
    st.markdown("## 📚 All Research Sessions")
    st.markdown("View all your previous research sessions.")
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=False):
        st.rerun()
    
    try:
        result = get_all_sessions()
        sessions = result.get('sessions', [])
        total = result.get('total', 0)
        
        if not sessions:
            st.info("No research sessions found. Start a new research to create your first session!")
        else:
            st.success(f"Found **{total}** research session(s)")
            
            # Display sessions in a grid
            for session in sessions:
                thread_id = session.get('thread_id', 'Unknown')
                user_query = session.get('user_query', 'No query')
                status = session.get('status', 'unknown')
                revision_count = session.get('revision_count', 0)
                has_final = session.get('has_final_response', False)
                
                # Status emoji
                status_emoji = {
                    "completed": "🟢",
                    "awaiting_approval": "🟡",
                    "researching": "🔵",
                    "pending": "⚪",
                    "unknown": "❓"
                }.get(status, "❓")
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"### `{thread_id}`")
                        # Truncate query if too long
                        display_query = user_query[:100] + "..." if len(user_query) > 100 else user_query
                        st.markdown(f"_{display_query}_")
                    
                    with col2:
                        st.markdown(f"**Status:** {status_emoji} `{status}`")
                        st.markdown(f"**Revisions:** {revision_count}")
                    
                    with col3:
                        if st.button("👁️ View", key=f"view_{thread_id}", use_container_width=True):
                            st.session_state['last_thread_id'] = thread_id
                            st.session_state['view_session'] = thread_id
                        
                        if status == "awaiting_approval":
                            if st.button("✅ Approve", key=f"approve_{thread_id}", use_container_width=True):
                                st.session_state['last_thread_id'] = thread_id
                                st.session_state['approve_session'] = thread_id
                    
                    st.divider()
            
            # Handle view session action
            if 'view_session' in st.session_state:
                thread_id = st.session_state.pop('view_session')
                st.markdown(f"---")
                st.markdown(f"### 🔍 Session Details: `{thread_id}`")
                
                session_data = get_session(thread_id)
                if session_data:
                    st.info(f"**Query:** {session_data.get('user_query', 'N/A')}")
                    display_status_badge(session_data.get('status', 'unknown'))
                    
                    if session_data.get('gathered_results'):
                        st.markdown("#### 📚 Results")
                        for item in session_data['gathered_results']:
                            with st.expander(f"Step {item['step_id']}: {item['query'][:50]}..."):
                                for i, res in enumerate(item['results']):
                                    st.markdown(f"**Finding {i+1}:** {res}")
                    
                    if session_data.get('final_response'):
                        st.markdown("#### 🎯 Final Response")
                        st.markdown(session_data['final_response'])
                else:
                    st.error(f"Could not load session: {thread_id}")
            
            # Handle approve session action
            if 'approve_session' in st.session_state:
                thread_id = st.session_state.pop('approve_session')
                st.markdown(f"---")
                st.markdown(f"### ✅ Approve Session: `{thread_id}`")
                
                feedback = st.text_area(
                    "Feedback (optional)",
                    placeholder="Add any feedback...",
                    key="quick_approve_feedback"
                )
                
                if st.button("✅ Confirm Approval", type="primary"):
                    with st.spinner("Generating final synthesis..."):
                        approval_result = approve_session(thread_id, True, feedback if feedback else None)
                        if 'detail' in approval_result:
                            st.error(f"❌ {approval_result['detail']}")
                        else:
                            st.success("✅ Session approved!")
                            if approval_result.get('final_response'):
                                st.markdown("#### 🎯 Final Response")
                                st.markdown(approval_result['final_response'])
                            st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error loading sessions: {str(e)}")


elif page == "📋 Check Session":
    st.markdown("## 📋 Check Session Status")
    st.markdown("Enter a thread ID to check the current state of a research session.")
    
    # Pre-fill with last thread ID if available
    default_thread_id = st.session_state.get('last_thread_id', '')
    
    thread_id = st.text_input(
        "Thread ID",
        value=default_thread_id,
        placeholder="e.g., abc12345"
    )
    
    if st.button("🔍 Check Status", use_container_width=True):
        if not thread_id:
            st.error("Please enter a thread ID")
        else:
            with st.spinner("Fetching session..."):
                try:
                    result = get_session(thread_id)
                    
                    if not result:
                        st.warning(f"Session not found: {thread_id}")
                    else:
                        # Header with status
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Thread ID", result.get('thread_id', 'N/A'))
                        with col2:
                            display_status_badge(result.get('status', 'unknown'))
                        with col3:
                            st.metric("Revisions", result.get('revision_count', 0))
                        
                        st.divider()
                        
                        # Original query
                        st.markdown("### 🎯 Research Query")
                        st.info(result.get('user_query', 'N/A'))
                        
                        # Gathered results
                        if result.get('gathered_results'):
                            st.markdown("### 📚 Gathered Results")
                            for item in result['gathered_results']:
                                with st.expander(f"Step {item['step_id']}: {item['query'][:50]}...", expanded=True):
                                    for i, res in enumerate(item['results']):
                                        st.markdown(f"**Finding {i+1}:** {res}")
                                    if item['sources']:
                                        st.markdown("**Sources:**")
                                        for src in item['sources']:
                                            st.markdown(f"- 🔗 [{src}]({src})")
                        
                        # Critique
                        if result.get('critique'):
                            st.markdown("### 📝 Critique Analysis")
                            critique = result['critique']
                            
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.metric("Score", f"{critique['score']:.0%}")
                            with col2:
                                st.progress(critique['score'])
                            
                            st.markdown(f"**Feedback:** {critique['feedback']}")
                            
                            if critique.get('should_refine'):
                                st.warning("⚠️ Further refinement recommended")
                            else:
                                st.success("✅ Quality threshold met")
                            
                            if critique['suggestions']:
                                st.markdown("**Improvement Suggestions:**")
                                for sug in critique['suggestions']:
                                    st.markdown(f"- 💡 {sug}")
                        
                        # Final response
                        if result.get('final_response'):
                            st.markdown("### 🎯 Final Response")
                            st.markdown(result['final_response'])
                        
                        # Approval status
                        if result.get('human_approved'):
                            st.success("✅ Human Approved")
                        elif result.get('status') == 'awaiting_approval':
                            st.warning("⏳ Awaiting Human Approval - Use the 'Approve Session' page")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


elif page == "✅ Approve Session":
    st.markdown("## ✅ Approve Research Session")
    st.markdown("Approve or provide feedback for sessions awaiting human review.")
    
    default_thread_id = st.session_state.get('last_thread_id', '')
    
    with st.form("approval_form"):
        thread_id = st.text_input(
            "Thread ID",
            value=default_thread_id,
            placeholder="e.g., abc12345"
        )
        
        approved = st.radio(
            "Decision",
            ["✅ Approve", "❌ Reject"],
            horizontal=True
        )
        
        feedback = st.text_area(
            "Feedback (optional)",
            placeholder="Focus more on practical applications...",
            help="Optional feedback to incorporate in final synthesis"
        )
        
        submitted = st.form_submit_button("Submit Decision", use_container_width=True)
        
        if submitted:
            if not thread_id:
                st.error("Please enter a thread ID")
            else:
                with st.spinner("Processing decision..."):
                    try:
                        is_approved = approved == "✅ Approve"
                        result = approve_session(
                            thread_id,
                            is_approved,
                            feedback if feedback else None
                        )
                        
                        if 'detail' in result:
                            st.error(f"❌ {result['detail']}")
                        else:
                            st.success(f"✅ {result.get('message', 'Decision processed')}")
                            
                            display_status_badge(result.get('status', 'unknown'))
                            
                            if result.get('final_response'):
                                st.markdown("### 🎯 Final Response")
                                st.markdown(result['final_response'])
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")


elif page == "🕐 Time Travel":
    st.markdown("## 🕐 Time Travel Debugging")
    st.markdown("View all checkpoints for a research session.")
    
    default_thread_id = st.session_state.get('last_thread_id', '')
    
    thread_id = st.text_input(
        "Thread ID",
        value=default_thread_id,
        placeholder="e.g., abc12345"
    )
    
    if st.button("🔍 Load Checkpoints", use_container_width=True):
        if not thread_id:
            st.error("Please enter a thread ID")
        else:
            with st.spinner("Loading checkpoints..."):
                try:
                    result = get_checkpoints(thread_id)
                    
                    st.markdown(f"### Checkpoints for `{result.get('thread_id', thread_id)}`")
                    
                    checkpoints = result.get('checkpoints', [])
                    
                    if not checkpoints:
                        st.info("No checkpoints found for this session.")
                    else:
                        st.success(f"Found {len(checkpoints)} checkpoint(s)")
                        
                        for i, cp in enumerate(checkpoints):
                            with st.expander(f"📍 Checkpoint {i+1}: `{cp.get('checkpoint_id', 'N/A')}`"):
                                st.json(cp.get('metadata', {}))
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


# Footer
st.divider()
st.markdown(
    """
    <div style="text-align: center; color: #6b7280; font-size: 0.85rem;">
        🔬 Research Assistant | Built with LangGraph + FastAPI + Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
