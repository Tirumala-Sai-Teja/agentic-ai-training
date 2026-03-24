import streamlit as st
import uuid
from src.graph import create_graph
from dotenv import load_dotenv
import os
from db_utils.database import init_db,get_all_extractions
import base64

log_placeholder = st.empty()
if "success_msg" not in st.session_state:
    st.session_state.success_msg = None

# Initialize DB
init_db()
agent=create_graph()
load_dotenv()

st.set_page_config(page_title="Cease & Desist - Document Agent", layout="wide")

# --- 1. SESSION STATE INITIALIZATION ---
# These must exist so Streamlit remembers what happened before the rerun
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "processing_active" not in st.session_state:
    st.session_state.processing_active = False

if st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    # Clear it so it doesn't show forever
    st.session_state.success_msg = None 

st.sidebar.title("Navigation Options")
page = st.sidebar.radio("Go to", ["1. See all extraction result","2. HITL Pending Reviews"])


if page == "1. See all extraction result":
    st.header("📊 Extraction History")
    df = get_all_extractions()
    
    if df.empty:
        st.warning("No extraction result(s) found in the database.")
    else:
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🔍 Detailed Extraction Result View")
        selected_id = st.selectbox("Select a Record ID to see full details", df['id'])
        
        if selected_id:
            detail = df[df['id'] == selected_id]['extracted_data'].values[0]
            st.json(detail)

elif page == "2. HITL Pending Reviews":
    st.header("⏳ Documents Awaiting Review")

    all_checkpoints = list(agent.checkpointer.list(config=None))

    latest_snapshots = {}
    for checkpoint in all_checkpoints:
        tid = checkpoint.config["configurable"]["thread_id"]
        # Since list() usually returns most recent first, we keep the first one we find
        if tid not in latest_snapshots:
            latest_snapshots[tid] = checkpoint
    
    active_interrupts = []
    for tid,t in latest_snapshots.items():
        conf = t.config
        snap = agent.get_state(conf)
        #print(snap.next)
        if snap.next and "human_review" in snap.next:
            active_interrupts.append({
                "thread_id": conf["configurable"]["thread_id"],
                "doc_name": snap.values.get("document_name", "Irrelevant"),
                "step": snap.next[0],
                "config": conf
            })

    if not active_interrupts:
        st.info("No documents currently require manual review.")
    else:
        selected_doc = st.selectbox(
            "Select a document to review:",
            active_interrupts,
            format_func=lambda x: f"{x['doc_name']} (Paused at: {x['step']}) - ID: {x['thread_id'][:8]}"
        )

        if selected_doc:
            thread_config = selected_doc["config"]
            snapshot = agent.get_state(thread_config)
            current_values = snapshot.values
            
            st.divider()
            st.subheader(f"Reviewing: {selected_doc['doc_name']}")

            col1, col2 = st.columns([3, 2])
            with col1:
                st.write("### 📄 Document Preview")
                doc_bytes = current_values.get("document_bytes")
                
                if doc_bytes:
                    # Encode PDF bytes to base64
                    base64_pdf = base64.b64encode(doc_bytes).decode('utf-8')
                    
                    # Embed PDF in an iframe
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                else:
                    st.warning("No PDF data found in state.")
            with col2:
                st.write("### 🛠️ Classification")
                classification = current_values.get('classification')

                #and round(classification.confidence,2) < round(float(os.getenv("CLASSIFICATION_CONFIDENCE_THRESHOLD_HITL")),2)
                if classification:
                    with st.form("hitl_cls_form"):
                        st.warning(f"Agent classified this document as '{classification.category}' with confidence '{classification.confidence}'")
                        st.warning(f"Classification Reason: '{classification.reason}'")
                        new_category = st.selectbox("Correct Type", ["Cease","Irrelevant"], 
                                                index=0)
                        submitted = st.form_submit_button("Confirm & Continue")
                        if submitted:
                            from src.schema import ClassificationResult
                            
                            current_state = agent.get_state(thread_config)
                            original_cls = current_state.values.get("classification")
                            
                            if original_cls:
                                updated_cls = original_cls.model_copy(update={
                                    "category": new_category, 
                                    "confidence": 1.0, 
                                    "reason": "Human Reviewed and classified",
                                    "is_human_reviewed": True
                                })
                            else:
                                st.error("No original classification found to update.")
                                st.stop()
                            try:
                                # update_state returns the config for the NEW checkpoint it just created
                                new_config = agent.update_state(
                                    thread_config, 
                                    {"classification": updated_cls}, 
                                    as_node="human_review"
                                )
                                # agent.update_state(
                                #     new_config, 
                                #     None, 
                                #     as_node="human_review"
                                # )

                                # 4. Resume using the updated config
                                with st.spinner("Processing decision..."):
                                    # stream(None) uses the last checkpoint in the provided config
                                    for event in agent.stream(None, config=new_config):
                                        st.write(event)
                                        # This should now trigger route_human_decision -> document_archive
                            except Exception as e:
                                st.error(f"Error updating graph: {e}")

                            st.success(f"Final Decision: {new_category}")
                            st.rerun()





