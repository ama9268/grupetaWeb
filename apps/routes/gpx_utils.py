import gpxpy


def parse_gpx(file_obj):
    gpx = gpxpy.parse(file_obj)

    moving_data = gpx.get_moving_data()
    uphill, downhill = gpx.get_uphill_downhill()

    track_points = []
    elevation_profile = []
    cumulative_distance = 0.0
    prev_point = None

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                track_points.append([point.latitude, point.longitude])
                if prev_point is not None and point.elevation is not None:
                    dist = point.distance_2d(prev_point) or 0
                    cumulative_distance += dist / 1000
                    elevation_profile.append({
                        'd': round(cumulative_distance, 3),
                        'e': round(point.elevation, 1),
                    })
                elif point.elevation is not None:
                    elevation_profile.append({'d': 0.0, 'e': round(point.elevation, 1)})
                prev_point = point

    return {
        'distance_km': round((moving_data.moving_distance or gpx.length_2d() or 0) / 1000, 2),
        'elevation_gain_m': round(uphill or 0),
        'elevation_loss_m': round(downhill or 0),
        'max_elevation_m': round(gpx.get_elevation_extremes().maximum or 0),
        'min_elevation_m': round(gpx.get_elevation_extremes().minimum or 0),
        'track_points': track_points,
        'elevation_profile': elevation_profile,
    }
