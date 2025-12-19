
print("Starting verification...")
try:
    from UI.pages.training_page import TrainingPage
    print("Import successful.")
    page = TrainingPage()
    print("Class instantiated.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
