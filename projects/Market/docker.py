#!/usr/bin/env python3
import json
import os
import datetime

# File where docket items will be stored
DOCKET_FILE = "docket.json"

def load_docket():
    """Load docket items from a JSON file."""
    if os.path.exists(DOCKET_FILE):
        with open(DOCKET_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error reading docket file. Starting with an empty docket.")
                return []
    else:
        return []

def save_docket(docket):
    """Save docket items to a JSON file."""
    with open(DOCKET_FILE, 'w') as f:
        json.dump(docket, f, indent=4)

def display_docket(docket):
    """Print out all docket items."""
    if not docket:
        print("\nNo docket items found.\n")
    else:
        print("\n--- Docket Items ---")
        for item in docket:
            print(f"ID: {item['id']}")
            print(f"Title: {item['title']}")
            print(f"Description: {item['description']}")
            print(f"Last Modified: {item['datetime']}")
            print("-" * 30)
        print()

def add_item(docket):
    """Add a new docket item."""
    title = input("Enter title: ").strip()
    description = input("Enter description: ").strip()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Determine a new unique id: if no items, start with 1; otherwise, max id + 1.
    new_id = max([item['id'] for item in docket], default=0) + 1
    docket.append({
        "id": new_id,
        "title": title,
        "description": description,
        "datetime": now
    })
    print("Docket item added.\n")

def edit_item(docket):
    """Edit an existing docket item."""
    try:
        item_id = int(input("Enter the ID of the item to edit: "))
    except ValueError:
        print("Invalid input. Please enter a numeric ID.\n")
        return

    for item in docket:
        if item['id'] == item_id:
            new_title = input(f"Enter new title (press Enter to keep '{item['title']}'): ").strip()
            new_desc = input(f"Enter new description (press Enter to keep '{item['description']}'): ").strip()
            if new_title:
                item['title'] = new_title
            if new_desc:
                item['description'] = new_desc
            # Update the last modified time
            item['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("Item updated.\n")
            return
    print("Item not found.\n")

def delete_item(docket):
    """Delete a docket item."""
    try:
        item_id = int(input("Enter the ID of the item to delete: "))
    except ValueError:
        print("Invalid input. Please enter a numeric ID.\n")
        return

    for i, item in enumerate(docket):
        if item['id'] == item_id:
            confirm = input(f"Are you sure you want to delete '{item['title']}'? (y/n): ").strip().lower()
            if confirm == 'y':
                docket.pop(i)
                print("Item deleted.\n")
            else:
                print("Deletion cancelled.\n")
            return
    print("Item not found.\n")

def main():
    docket = load_docket()

    while True:
        print("=== Docket Program ===")
        print("1. View Docket Items")
        print("2. Add Docket Item")
        print("3. Edit Docket Item")
        print("4. Delete Docket Item")
        print("5. Save and Exit")
        choice = input("Enter your choice (1-5): ").strip()

        if choice == '1':
            display_docket(docket)
        elif choice == '2':
            add_item(docket)
        elif choice == '3':
            edit_item(docket)
        elif choice == '4':
            delete_item(docket)
        elif choice == '5':
            save_docket(docket)
            print("Docket saved. Exiting program.")
            break
        else:
            print("Invalid choice, please try again.\n")

if __name__ == "__main__":
    main()
