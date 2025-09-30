"""
Tests for the joke generation module.

Following TDD principles with comprehensive test coverage.
"""

import pytest

from joke_mcp_server.jokes import JokeGenerator, DAD_JOKES, MOM_JOKES


class TestJokeGenerator:
    """Test suite for JokeGenerator class."""

    def test_initialization(self):
        """Test that JokeGenerator initializes correctly."""
        generator = JokeGenerator()
        assert generator is not None

    def test_initialization_with_seed(self):
        """Test that JokeGenerator accepts a seed for reproducibility."""
        generator = JokeGenerator(seed=42)
        assert generator is not None

    def test_get_dad_joke_returns_string(self):
        """Test that get_dad_joke returns a string."""
        generator = JokeGenerator()
        joke = generator.get_dad_joke()
        assert isinstance(joke, str)
        assert len(joke) > 0

    def test_get_dad_joke_from_collection(self):
        """Test that get_dad_joke returns a joke from the dad jokes collection."""
        generator = JokeGenerator()
        joke = generator.get_dad_joke()
        assert joke in DAD_JOKES

    def test_get_mom_joke_returns_string(self):
        """Test that get_mom_joke returns a string."""
        generator = JokeGenerator()
        joke = generator.get_mom_joke()
        assert isinstance(joke, str)
        assert len(joke) > 0

    def test_get_mom_joke_from_collection(self):
        """Test that get_mom_joke returns a joke from the mom jokes collection."""
        generator = JokeGenerator()
        joke = generator.get_mom_joke()
        assert joke in MOM_JOKES

    def test_reproducibility_with_seed(self):
        """Test that using the same seed produces the same jokes."""
        generator1 = JokeGenerator(seed=42)
        generator2 = JokeGenerator(seed=42)

        # Get multiple jokes to ensure reproducibility
        jokes1 = [generator1.get_dad_joke() for _ in range(5)]
        jokes2 = [generator2.get_dad_joke() for _ in range(5)]

        assert jokes1 == jokes2

    def test_get_joke_with_dad_type(self):
        """Test get_joke method with 'dad' type."""
        generator = JokeGenerator()
        joke = generator.get_joke("dad")
        assert joke in DAD_JOKES

    def test_get_joke_with_mom_type(self):
        """Test get_joke method with 'mom' type."""
        generator = JokeGenerator()
        joke = generator.get_joke("mom")
        assert joke in MOM_JOKES

    def test_get_joke_with_invalid_type(self):
        """Test that get_joke raises ValueError for invalid type."""
        generator = JokeGenerator()
        with pytest.raises(ValueError) as exc_info:
            generator.get_joke("invalid")
        assert "Invalid joke type" in str(exc_info.value)

    def test_randomness(self):
        """Test that jokes are randomly selected (statistical test)."""
        generator = JokeGenerator()
        jokes = [generator.get_dad_joke() for _ in range(20)]

        # With 10 dad jokes and 20 selections, we should get at least 2 unique jokes
        unique_jokes = set(jokes)
        assert len(unique_jokes) >= 2

    def test_dad_jokes_collection_not_empty(self):
        """Test that DAD_JOKES collection is not empty."""
        assert len(DAD_JOKES) > 0

    def test_mom_jokes_collection_not_empty(self):
        """Test that MOM_JOKES collection is not empty."""
        assert len(MOM_JOKES) > 0

    def test_all_dad_jokes_are_strings(self):
        """Test that all dad jokes in the collection are strings."""
        for joke in DAD_JOKES:
            assert isinstance(joke, str)
            assert len(joke) > 0

    def test_all_mom_jokes_are_strings(self):
        """Test that all mom jokes in the collection are strings."""
        for joke in MOM_JOKES:
            assert isinstance(joke, str)
            assert len(joke) > 0