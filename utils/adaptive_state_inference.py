"""
Behavioral State Inference Engine for Adaptive AI

Detects Darrian's neurological state (bipolar, ADHD, anxiety) from interaction patterns
without requiring self-reporting. Infers state from:
- Message urgency (exclamation marks, ALL CAPS, rapid-fire)
- Task switching frequency
- Typing speed (WPM)
- Response latency
- Sentence structure
- Emoji density
- Sleep integration

Reference: BRD_NEUROSCIENCE_ADAPTIVE_AI_SYSTEM_2026Q2.md
"""

import re
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class InteractionSignals:
    """Container for behavioral signals extracted from a single interaction."""
    
    # Message content signals
    urgency_score: float  # 0.0-1.0: exclamation marks, caps, rapid pacing
    typing_speed_wpm: float  # Words per minute (inferred from message length + time)
    avg_sentence_length: float  # Characters per sentence
    emoji_density: float  # Emojis per 100 chars
    question_mark_density: float  # Question marks per 100 chars
    caps_density: float  # CAPS words per 100 words
    
    # Timing signals
    time_since_last_message_sec: float  # Seconds since previous interaction (-1 if no history)
    message_length: int  # Character count
    time_to_compose_sec: float  # How long to write message (-1 if unknown)
    
    # Context signals
    task_switch_count_5min: int  # How many page/task switches in past 5 minutes
    hours_of_sleep_last_night: Optional[float]  # From Health Hub integration
    time_of_day_hour: int  # 0-23
    
    # Flags
    all_caps: bool  # Is entire message in CAPS?
    is_fragmented: bool  # Sentence fragments or extreme short sentences?
    rapid_fire: bool  # Multiple messages in <30 sec?


class SignalDetectors:
    """Stateless signal extraction functions."""
    
    @staticmethod
    def extract_urgency(message: str) -> float:
        """
        Detect message urgency from punctuation + formatting.
        High urgency = exclamation marks, multiple question marks, ALL CAPS
        """
        if not message:
            return 0.0
        
        exclamation_count = message.count('!')
        multi_question_count = message.count('??')
        caps_words = len([w for w in message.split() if w.isupper() and len(w) > 1])
        total_words = len(message.split())
        
        # Normalize scores to 0.0-1.0
        exclamation_score = min(exclamation_count / 3, 1.0)  # Lower threshold for exclamations
        question_score = min(multi_question_count / 2, 1.0)  # Lower threshold for questions
        caps_score = (caps_words / max(total_words, 1)) * 0.5  # Weight caps less
        
        urgency = (exclamation_score * 0.4 + question_score * 0.4 + caps_score * 0.2)
        return min(urgency, 1.0)
    
    @staticmethod
    def extract_typing_speed(message: str, time_to_compose_sec: float) -> float:
        """
        Infer typing speed in 'evidence units' (0.0-1.0).
        - < 5 sec to type message = very fast (hyperfocus/manic) = 1.0
        - 5-15 sec = normal (baseline) = 0.5
        - > 30 sec = slow (anxiety/depression) = 0.0
        
        Returns normalized score, not actual WPM, for state detection.
        """
        if time_to_compose_sec <= 0:
            return 0.5  # Unknown, assume baseline
        
        # Map time to speed score
        if time_to_compose_sec < 5:
            return 1.0
        elif time_to_compose_sec < 15:
            return 0.5
        elif time_to_compose_sec < 30:
            return 0.25
        else:
            return 0.0
    
    @staticmethod
    def extract_sentence_length(message: str) -> float:
        """
        Average sentence length in characters.
        Scattered state = short sentences. Focused = longer. Manic = chaotic mix.
        Returns normalized avg (0.0-100.0 scale, capped at 1.0 for state inference).
        """
        sentences = re.split(r'[.!?]+', message)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        # Normalize: 0-35 chars/sentence is baseline, cap at 1.0
        return min(avg_len / 35, 1.0)
    
    @staticmethod
    def extract_emoji_density(message: str) -> float:
        """
        Count emojis per 100 characters.
        Manic/anxious = more emojis. Depressed = fewer.
        Returns normalized score 0.0-1.0.
        """
        # Emoji regex: broad pattern for Unicode emoji ranges
        emoji_pattern = r'[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F1E0-\U0001F1FF]'
        emoji_count = len(re.findall(emoji_pattern, message))
        
        if not message:
            return 0.0
        
        density = (emoji_count / len(message)) * 100
        # Normalize: 1-2 emojis per 100 chars is "normal"
        # Max out at 1.0 if density is high
        return min(density / 4, 1.0)
    
    @staticmethod
    def extract_question_mark_density(message: str) -> float:
        """
        Question marks per 100 characters.
        High density = anxiety (seeking reassurance). Low = depressed (no questions).
        Returns normalized 0.0-1.0.
        """
        if not message:
            return 0.0
        
        question_count = message.count('?')
        density = (question_count / len(message)) * 100
        
        # Normalize: 2-3 per 100 chars is high
        return min(density / 3, 1.0)
    
    @staticmethod
    def extract_caps_density(message: str) -> float:
        """
        Fraction of words in ALL CAPS.
        High = urgency/manic. Low = baseline/depressed.
        Returns 0.0-1.0.
        """
        words = message.split()
        if not words:
            return 0.0
        
        caps_words = sum(1 for w in words if w.isupper() and len(w) > 1)
        density = caps_words / len(words)
        # Cap at 0.5 to avoid extremes
        return min(density, 0.5)
    
    @staticmethod
    def extract_task_switch_frequency(
        current_page: Optional[int],
        page_visit_history: list[Tuple[int, float]]  # [(page_id, timestamp_sec), ...]
    ) -> int:
        """
        Count task/page switches in past 5 minutes.
        Returns integer count.
        """
        if not page_visit_history or current_page is None:
            return 0
        
        now = datetime.now().timestamp()
        five_min_ago = now - 300  # 5 minutes
        
        recent_visits = [(page, ts) for page, ts in page_visit_history if ts >= five_min_ago]
        unique_pages = set(page for page, _ in recent_visits)
        
        # Count switches (transitions between different pages)
        if not recent_visits:
            return 0
        
        switches = 0
        for i in range(1, len(recent_visits)):
            if recent_visits[i][0] != recent_visits[i-1][0]:
                switches += 1
        
        return switches
    
    @staticmethod
    def extract_is_fragmented(message: str) -> bool:
        """
        Check if message shows signs of fragmentation (scattered thinking).
        Fragmentation = very short sentences (avg < 10 chars) OR sentence fragments.
        """
        sentences = re.split(r'[.!?]+', message)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return False
        
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        fragmented = avg_len < 10  # Very short sentences
        
        # Also check for fragments (no verb structure)
        fragment_patterns = r'^(Yeah|No|Ok|Hmm|What|Why|How|Ugh|Wow)\s*$'
        fragments = sum(1 for s in sentences if re.match(fragment_patterns, s))
        
        return fragmented or (fragments > len(sentences) * 0.3)
    
    @staticmethod
    def extract_rapid_fire(
        time_since_last_message_sec: float,
        rapid_fire_threshold_sec: float = 30.0
    ) -> bool:
        """Check if messages are coming in rapid succession (potential manic/scattered)."""
        return 0 < time_since_last_message_sec < rapid_fire_threshold_sec


class StateScorer:
    """Weighted state scoring based on signals."""
    
    STATES = ['hyperfocus', 'adhd_scatter', 'manic', 'anxiety', 'depressed', 'baseline']
    CONFIDENCE_THRESHOLD = 0.65
    
    @staticmethod
    def score_states(signals: InteractionSignals) -> Dict[str, float]:
        """
        Score each state based on behavioral signals.
        Returns dict of state -> confidence (0.0-1.0).
        """
        
        # Hyperfocus: High urgency + fast typing + sustained focus
        hyperfocus_score = (
            0.3 * signals.urgency_score +
            0.3 * signals.typing_speed_wpm +
            0.4 * (1.0 - signals.task_switch_count_5min / max(5, signals.task_switch_count_5min + 1))
        )
        
        # ADHD Scatter: High task switching + fragmented thinking + urgency spikes
        scatter_score = (
            0.4 * min(signals.task_switch_count_5min / 5, 1.0) +
            0.3 * (1.0 if signals.is_fragmented else 0.0) +
            0.3 * signals.urgency_score
        )
        
        # Manic: High urgency + emojis + low sleep + caps + rapid-fire messages
        manic_score = (
            0.3 * signals.urgency_score +
            0.2 * signals.emoji_density +
            0.2 * signals.caps_density +
            0.1 * (1.0 if signals.rapid_fire else 0.0) +
            0.2 * (
                (1.0 - (signals.hours_of_sleep_last_night or 7) / 8)
                if signals.hours_of_sleep_last_night else 0.0
            )
        )
        
        # Anxiety: High question mark density + fragmentation + latency (waiting to respond)
        anxiety_score = (
            0.4 * signals.question_mark_density +
            0.3 * (1.0 if signals.is_fragmented else 0.0) +
            0.3 * (1.0 if signals.time_since_last_message_sec > 60 else 0.5)
        )
        
        # Depressed: Low emoji + low urgency + late night activity + long response times
        depressed_score = (
            0.3 * (1.0 - signals.emoji_density) +
            0.3 * (1.0 - signals.urgency_score) +
            0.2 * (1.0 if signals.time_of_day_hour >= 22 or signals.time_of_day_hour <= 6 else 0.2) +
            0.2 * (0.0 if signals.typing_speed_wpm > 0.5 else 1.0)  # Slow typing
        )
        
        # Baseline: Even, moderate signals across all components
        state_scores = {
            'hyperfocus': min(hyperfocus_score, 1.0),
            'adhd_scatter': min(scatter_score, 1.0),
            'manic': min(manic_score, 1.0),
            'anxiety': min(anxiety_score, 1.0),
            'depressed': min(depressed_score, 1.0),
        }
        
        # Baseline = inverse of max of other states
        max_other = max(state_scores.values())
        state_scores['baseline'] = 1.0 - max_other
        
        return state_scores
    
    @staticmethod
    def determine_state(
        state_scores: Dict[str, float]
    ) -> Tuple[str, float]:
        """
        Select the state with highest confidence.
        Only return if confidence >= threshold, else return 'baseline'.
        
        Returns (state_name, confidence_score)
        """
        max_state = max(state_scores, key=state_scores.get)
        max_confidence = state_scores[max_state]
        
        if max_confidence >= StateScorer.CONFIDENCE_THRESHOLD:
            return max_state, max_confidence
        else:
            return 'baseline', state_scores['baseline']


def infer_state(
    signals_dict: Dict[str, any],
    page_visit_history: Optional[list[Tuple[int, float]]] = None
) -> Tuple[str, float]:
    """
    Infer Darrian's current neurological state from interaction signals.
    
    Args:
        signals_dict: Dictionary with keys:
            - urgency_score (0.0-1.0)
            - typing_speed_wpm (0.0-1.0)
            - avg_sentence_length (0.0-1.0)
            - emoji_density (0.0-1.0)
            - question_mark_density (0.0-1.0)
            - caps_density (0.0-1.0)
            - time_since_last_message_sec (float, -1 if unknown)
            - message_length (int)
            - time_to_compose_sec (float, -1 if unknown)
            - task_switch_count_5min (int)
            - hours_of_sleep_last_night (float or None)
            - time_of_day_hour (0-23)
            - is_fragmented (bool)
            - is_rapid_fire (bool)
        
        page_visit_history: Optional history of page visits for context
    
    Returns:
        (state_name, confidence_score)
        E.g., ('manic', 0.72) or ('baseline', 0.55)
    """
    
    # Build InteractionSignals object
    signals = InteractionSignals(
        urgency_score=signals_dict.get('urgency_score', 0.0),
        typing_speed_wpm=signals_dict.get('typing_speed_wpm', 0.5),
        avg_sentence_length=signals_dict.get('avg_sentence_length', 0.5),
        emoji_density=signals_dict.get('emoji_density', 0.0),
        question_mark_density=signals_dict.get('question_mark_density', 0.0),
        caps_density=signals_dict.get('caps_density', 0.0),
        time_since_last_message_sec=signals_dict.get('time_since_last_message_sec', -1),
        message_length=signals_dict.get('message_length', 0),
        time_to_compose_sec=signals_dict.get('time_to_compose_sec', -1),
        task_switch_count_5min=signals_dict.get('task_switch_count_5min', 0),
        hours_of_sleep_last_night=signals_dict.get('hours_of_sleep_last_night'),
        time_of_day_hour=signals_dict.get('time_of_day_hour', datetime.now().hour),
        all_caps=signals_dict.get('all_caps', False),
        is_fragmented=signals_dict.get('is_fragmented', False),
        rapid_fire=signals_dict.get('is_rapid_fire', signals_dict.get('rapid_fire', False)),
    )
    
    # Score states
    state_scores = StateScorer.score_states(signals)
    
    # Determine final state
    detected_state, confidence = StateScorer.determine_state(state_scores)
    
    return detected_state, confidence


def build_signals_from_message(
    message: str,
    time_to_compose_sec: float = -1,
    time_since_last_message_sec: float = -1,
    task_switch_count_5min: int = 0,
    hours_of_sleep_last_night: Optional[float] = None,
) -> Dict[str, any]:
    """
    Helper: Extract all signals from a raw message string.
    
    Args:
        message: Raw user message text
        time_to_compose_sec: How long to write (seconds)
        time_since_last_message_sec: Time since last interaction
        task_switch_count_5min: Tracked externally
        hours_of_sleep_last_night: From Health Hub
    
    Returns:
        Dictionary suitable for infer_state()
    """
    
    detectors = SignalDetectors()
    
    signals = {
        'urgency_score': detectors.extract_urgency(message),
        'typing_speed_wpm': detectors.extract_typing_speed(message, time_to_compose_sec),
        'avg_sentence_length': detectors.extract_sentence_length(message),
        'emoji_density': detectors.extract_emoji_density(message),
        'question_mark_density': detectors.extract_question_mark_density(message),
        'caps_density': detectors.extract_caps_density(message),
        'time_since_last_message_sec': time_since_last_message_sec,
        'message_length': len(message),
        'time_to_compose_sec': time_to_compose_sec,
        'task_switch_count_5min': task_switch_count_5min,
        'hours_of_sleep_last_night': hours_of_sleep_last_night,
        'time_of_day_hour': datetime.now().hour,
        'all_caps': message.isupper() and len(message.replace(' ', '')) > 0,
        'is_fragmented': detectors.extract_is_fragmented(message),
        'is_rapid_fire': detectors.extract_rapid_fire(time_since_last_message_sec),
    }
    
    return signals


if __name__ == '__main__':
    # Quick test
    test_message = "OMG YES!!! This is AMAZING!! I can't wait to build this!!!"
    signals = build_signals_from_message(
        test_message,
        time_to_compose_sec=3.0,
        time_since_last_message_sec=5.0,
        hours_of_sleep_last_night=5.0,
    )
    
    state, confidence = infer_state(signals)
    print(f"Detected state: {state} (confidence: {confidence:.2f})")
    print(f"Signals: {signals}")
