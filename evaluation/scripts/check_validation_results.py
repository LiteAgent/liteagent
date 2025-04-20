#!/usr/bin/env python3
import json
from collections import defaultdict

def main():
    # Load the JSON file
    with open("validation_results.json", "r") as f:
        data = json.load(f)

    # Initialize a stats dictionary for each agent.
    # Each agent will have counters and a list of comparison records.
    stats = defaultdict(lambda: {
        "correct": 0,
        "incorrect": 0,
        "mismatches": 0,
        "comparisons": []
    })

    # Process each record in the JSON list.
    for record in data:
        agent = record.get("agent", "unknown")
        task = record.get("task", "")
        details = record.get("details", [])
        
        # Process each detail entry.
        for detail in details:
            # Determine which field to use as the expected value.
            # If a "db" field exists, we use that; otherwise, we fall back on "scratchpad".
            expected = detail.get("db")
            source_field = "db"
            if expected is None:
                expected = detail.get("scratchpad")
                source_field = "scratchpad"
            
            # Get the manual verification result.
            manual = detail.get("manual_verification")
            
            # Prepare a record of this comparison.
            comparison = {
                "task": task,
                "source_field": source_field,
                "expected": expected,
                "manual": manual,
                "match": (expected == manual),
                "extra_details": detail.get("extra_details", ""),
                "source_directory": detail.get("source_directory", ""),
                "target_directory": detail.get("target_directory", "")
            }
            stats[agent]["comparisons"].append(comparison)
            
            # Update counts.
            if expected == manual:
                # When both values agree, we count based on the value.
                if expected == "correct":
                    stats[agent]["correct"] += 1
                elif expected == "incorrect":
                    stats[agent]["incorrect"] += 1
                # If both agree on some other string, you might choose to handle it differently.
            else:
                # They disagree; record as a mismatch.
                stats[agent]["mismatches"] += 1

    # Output the full statistics.
    for agent, agent_stats in stats.items():
        print(f"Agent: {agent}")
        print(f"  Correct count (expected & manual = 'correct'): {agent_stats['correct']}")
        print(f"  Incorrect count (expected & manual = 'incorrect'): {agent_stats['incorrect']}")
        print(f"  Mismatches (disagreement between expected and manual): {agent_stats['mismatches']}")
        print("  Comparisons:")
        for comp in agent_stats["comparisons"]:
            print(f"    Task: {comp['task']}")
            print(f"      Source field used: {comp['source_field']}")
            print(f"      Expected: {comp['expected']}  |  Manual: {comp['manual']}  |  Match: {comp['match']}")
            if comp["extra_details"]:
                print(f"      Extra details: {comp['extra_details']}")
            if comp["source_directory"]:
                print(f"      Source directory: {comp['source_directory']}")
            if comp["target_directory"]:
                print(f"      Target directory: {comp['target_directory']}")
        print("\n")

if __name__ == "__main__":
    main()
