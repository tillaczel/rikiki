#!/usr/bin/env python3
"""
Script to update existing games in the database with current timestamps.
This fixes games that don't have started_at or ended_at timestamps.
"""

from app import app, db, Game
from datetime import datetime, timezone

def update_game_timestamps():
    """Update existing games with current timestamps if they're missing."""
    with app.app_context():
        # Get all games
        games = Game.query.all()
        updated_count = 0
        
        print(f"Found {len(games)} games in database")
        
        for game in games:
            updated = False
            
            # Set started_at if missing and game has rounds
            if not game.started_at and game.rounds:
                game.started_at = datetime.now(timezone.utc)
                updated = True
                print(f"  Game {game.id}: Set started_at")
            
            # Set ended_at if missing and game is not active
            if not game.ended_at and not game.is_active:
                game.ended_at = datetime.now(timezone.utc)
                updated = True
                print(f"  Game {game.id}: Set ended_at")
            
            if updated:
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✅ Updated {updated_count} games with timestamps")
        else:
            print("\n✅ All games already have proper timestamps")
        
        # Show summary
        print("\n📊 Database Summary:")
        total_games = Game.query.count()
        active_games = Game.query.filter_by(is_active=True).count()
        completed_games = Game.query.filter_by(is_active=False).count()
        games_with_started = Game.query.filter(Game.started_at.isnot(None)).count()
        games_with_ended = Game.query.filter(Game.ended_at.isnot(None)).count()
        
        print(f"  Total games: {total_games}")
        print(f"  Active games: {active_games}")
        print(f"  Completed games: {completed_games}")
        print(f"  Games with started_at: {games_with_started}")
        print(f"  Games with ended_at: {games_with_ended}")

if __name__ == "__main__":
    print("🔄 Updating game timestamps in database...")
    update_game_timestamps()
    print("\n✨ Timestamp update complete!") 