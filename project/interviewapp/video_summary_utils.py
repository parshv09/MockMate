def compute_video_confidence(stats):
    total = max(1, stats["total_frames"])

    presence_pct = (stats["face_present_frames"] / total) * 100
    eye_pct = (stats["eye_contact_frames"] / total) * 100
    movement_pct = (stats["head_movement_frames"] / total) * 100

    # Confidence score logic
    confidence_score = (
        presence_pct * 0.4 +
        eye_pct * 0.4 +
        (100 - movement_pct) * 0.2
    )

    confidence_score = round(confidence_score, 2)

    # Engagement label
    if confidence_score >= 80:
        level = "Excellent"
    elif confidence_score >= 60:
        level = "Good"
    elif confidence_score >= 40:
        level = "Average"
    else:
        level = "Needs Improvement"

    # Suggestions
    tips = []
    if presence_pct < 70:
        tips.append("Stay in front of the camera throughout the interview.")
    if eye_pct < 60:
        tips.append("Maintain better eye contact while answering.")
    if movement_pct > 40:
        tips.append("Avoid excessive head movement to appear confident.")

    if not tips:
        tips.append("Great confidence and engagement throughout the interview.")

    return {
        "confidence_score": confidence_score,
        "engagement_level": level,
        "presence_pct": round(presence_pct, 1),
        "eye_contact_pct": round(eye_pct, 1),
        "movement_pct": round(movement_pct, 1),
        "tips": tips
    }
