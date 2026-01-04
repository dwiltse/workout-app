#!/usr/bin/env python3
"""
Fitbit GPS Route Viewer
Simple utility to view and export GPS routes from your Fitbit data
"""

import psycopg2
import json
from datetime import datetime, timedelta

def get_routes(db_conn, days_back=30):
    """Get GPS routes from the database"""
    conn = psycopg2.connect(db_conn)
    cur = conn.cursor()

    # Get routes from last N days
    start_date = datetime.now().date() - timedelta(days=days_back)

    cur.execute("""
        SELECT
            r.exercise_log_id,
            r.activity_name,
            r.route_date,
            r.start_latitude,
            r.start_longitude,
            r.end_latitude,
            r.end_longitude,
            r.total_distance_miles,
            r.total_elevation_gain_feet,
            r.max_speed_mph,
            r.gps_points_count,
            e.duration_minutes,
            e.calories
        FROM fitbit_routes r
        JOIN fitbit_exercises e ON r.exercise_log_id = e.exercise_log_id
        WHERE r.route_date >= %s
        ORDER BY r.route_date DESC, e.start_time DESC
    """, (start_date,))

    routes = cur.fetchall()

    cur.close()
    conn.close()

    return routes

def get_gps_points(db_conn, exercise_log_id):
    """Get detailed GPS points for a specific exercise"""
    conn = psycopg2.connect(db_conn)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            time_offset_seconds,
            latitude,
            longitude,
            altitude_feet,
            distance_miles,
            heart_rate,
            speed_mph,
            recorded_at
        FROM fitbit_gps_points
        WHERE exercise_log_id = %s
        ORDER BY time_offset_seconds
    """, (exercise_log_id,))

    points = cur.fetchall()

    cur.close()
    conn.close()

    return points

def export_route_geojson(db_conn, exercise_log_id, output_file=None):
    """Export a route as GeoJSON for mapping applications"""
    points = get_gps_points(db_conn, exercise_log_id)

    if not points:
        print(f"No GPS points found for exercise {exercise_log_id}")
        return None

    # Convert to GeoJSON format
    coordinates = []
    for point in points:
        time_offset, lat, lng, altitude, distance, hr, speed, recorded_at = point
        if lat is not None and lng is not None:
            # GeoJSON format: [longitude, latitude, altitude]
            coord = [float(lng), float(lat)]
            if altitude is not None:
                coord.append(float(altitude))
            coordinates.append(coord)

    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        },
        "properties": {
            "exercise_log_id": exercise_log_id,
            "points_count": len(coordinates),
            "start_time": points[0][7].isoformat() if points[0][7] else None,
            "end_time": points[-1][7].isoformat() if points[-1][7] else None,
            "total_distance_miles": points[-1][4] if points[-1][4] else 0
        }
    }

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=2)
        print(f"✓ Route exported to {output_file}")

    return geojson

def print_routes_summary(routes):
    """Print a summary of available routes"""
    if not routes:
        print("No GPS routes found in the database.")
        return

    print(f"\n=== Found {len(routes)} GPS Routes ===\n")

    for route in routes:
        (log_id, activity, date, start_lat, start_lng, _, _,
         distance, elevation, max_speed, points, duration, calories) = route

        print(f"📍 {activity} - {date}")
        print(f"   ID: {log_id}")
        print(f"   Distance: {distance:.2f} mi")
        print(f"   Duration: {duration} min")
        print(f"   Calories: {calories}")
        print(f"   Elevation Gain: {elevation:.0f} ft")
        print(f"   Max Speed: {max_speed:.1f} mph")
        print(f"   GPS Points: {points}")
        print(f"   Start: {start_lat:.6f}, {start_lng:.6f}")
        print()

def main():
    print("=== Fitbit GPS Route Viewer ===\n")

    # Database connection
    db_conn = input("Enter your Neon DB Connection String: ").strip()
    if not db_conn or "user:password" in db_conn:
        print("Please provide a valid Neon database connection string")
        return

    # Get routes
    days_back = input("Days back to search [default: 30]: ").strip()
    days_back = int(days_back) if days_back.isdigit() else 30

    try:
        routes = get_routes(db_conn, days_back)
        print_routes_summary(routes)

        if routes:
            print("Commands:")
            print("  export <exercise_id> [filename.geojson] - Export route as GeoJSON")
            print("  points <exercise_id> - Show detailed GPS points")
            print("  quit - Exit")

            while True:
                command = input("\nEnter command: ").strip().split()

                if not command or command[0] == 'quit':
                    break

                elif command[0] == 'export' and len(command) >= 2:
                    exercise_id = int(command[1])
                    filename = command[2] if len(command) > 2 else f"fitbit_route_{exercise_id}.geojson"
                    export_route_geojson(db_conn, exercise_id, filename)

                elif command[0] == 'points' and len(command) == 2:
                    exercise_id = int(command[1])
                    points = get_gps_points(db_conn, exercise_id)

                    if points:
                        print(f"\n=== GPS Points for Exercise {exercise_id} ===")
                        print("Time(s)  | Lat       | Lng        | Alt(ft) | Dist(mi) | HR  | Speed")
                        print("-" * 70)

                        for point in points[:20]:  # Show first 20 points
                            time_offset, lat, lng, altitude, distance, hr, speed, _ = point
                            lat_str = f"{lat:.6f}" if lat else "N/A"
                            lng_str = f"{lng:.6f}" if lng else "N/A"
                            alt_str = f"{altitude:.0f}" if altitude else "N/A"
                            dist_str = f"{distance:.3f}" if distance else "N/A"
                            hr_str = str(hr) if hr else "N/A"
                            speed_str = f"{speed:.1f}" if speed else "N/A"

                            print(f"{time_offset:7d} | {lat_str:9s} | {lng_str:10s} | {alt_str:7s} | {dist_str:8s} | {hr_str:3s} | {speed_str}")

                        if len(points) > 20:
                            print(f"... and {len(points) - 20} more points")
                    else:
                        print(f"No GPS points found for exercise {exercise_id}")

                else:
                    print("Invalid command. Use: export <id> [filename], points <id>, or quit")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()