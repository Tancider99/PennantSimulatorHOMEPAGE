
try:
    from UI.widgets.tables import DraggableTableWidget, DefenseDelegate
    print("SUCCESS: Imported DraggableTableWidget and DefenseDelegate")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"FAILURE: {e}")
