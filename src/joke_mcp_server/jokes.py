"""
Joke generation module providing dad and mom jokes.

This module contains curated collections of dad and mom jokes
with random selection functionality.
"""

import random
from typing import Literal

# Curated collection of dad jokes
DAD_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "I used to hate facial hair, but then it grew on me.",
    "Why don't eggs tell jokes? They'd crack each other up!",
    "I'm afraid for the calendar. Its days are numbered.",
    "What do you call a fake noodle? An impasta!",
    "Why did the bicycle fall over? Because it was two-tired!",
    "I only know 25 letters of the alphabet. I don't know y.",
    "What did the ocean say to the beach? Nothing, it just waved.",
]

# Curated collection of mom jokes
MOM_JOKES = [
    "I brought you into this world, and I can take you out of it!",
    "Because I said so, that's why!",
    "If your friends jumped off a bridge, would you do it too?",
    "I'm not just talking to hear myself speak!",
    "Money doesn't grow on trees, you know!",
    "Don't make me turn this car around!",
    "You'll understand when you're older.",
    "I'm not your maid! Clean up after yourself!",
    "Close the door! Were you raised in a barn?",
    "If you can't say something nice, don't say anything at all.",
]


class JokeGenerator:
    """
    A class for generating random jokes.

    Supports both dad jokes and mom jokes with proper type safety.
    """

    def __init__(self, seed: int | None = None):
        """
        Initialize the joke generator.

        Args:
            seed: Optional random seed for reproducible joke selection
        """
        self._random = random.Random(seed)

    def get_dad_joke(self) -> str:
        """
        Get a random dad joke.

        Returns:
            A string containing a dad joke
        """
        return self._random.choice(DAD_JOKES)

    def get_mom_joke(self) -> str:
        """
        Get a random mom joke.

        Returns:
            A string containing a mom joke
        """
        return self._random.choice(MOM_JOKES)

    def get_joke(self, joke_type: Literal["dad", "mom"]) -> str:
        """
        Get a random joke of the specified type.

        Args:
            joke_type: The type of joke to retrieve ("dad" or "mom")

        Returns:
            A string containing the requested joke

        Raises:
            ValueError: If joke_type is not "dad" or "mom"
        """
        if joke_type == "dad":
            return self.get_dad_joke()
        elif joke_type == "mom":
            return self.get_mom_joke()
        else:
            raise ValueError(f"Invalid joke type: {joke_type}. Must be 'dad' or 'mom'.")