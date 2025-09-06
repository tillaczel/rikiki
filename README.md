# 🎴 Rikiki Card Game App

A web-based application for managing Rikiki card games with player registration, game tracking, and detailed player statistics.

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

## Game Rules

- **Cards**: 52-card deck (1 trump card, 51 cards distributed)
- **Rounds**: Cards per player goes 1 → 2 → 3 → ... → max → ... → 3 → 2 → 1
- **Max Cards**: `floor(51 / number_of_players)`
- **Total Rounds**: `(max_cards × 2) - 1`
- **Scoring**:
  - Correct guess: `10 + 2 × hits` points
  - Wrong guess: `-2 × |guess - hits|` points