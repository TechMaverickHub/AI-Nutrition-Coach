"""Hermetic metadata assertions for the domain models."""

from app.core.database import Base
from app.models import FoodItem, Goal, Meal, User


def test_expected_tables_registered() -> None:
    tables = set(Base.metadata.tables)
    assert {"users", "meals", "food_items", "goals"} <= tables


def test_meal_columns_and_fk_cascade() -> None:
    meals = Base.metadata.tables["meals"]
    assert {"id", "user_id", "meal_type", "meal_time", "image_url", "created_at"} == set(
        meals.columns.keys()
    )
    user_fk = next(iter(meals.c.user_id.foreign_keys))
    assert user_fk.column.table.name == "users"
    assert user_fk.ondelete == "CASCADE"


def test_food_item_columns_and_fk_cascade() -> None:
    food_items = Base.metadata.tables["food_items"]
    assert {"id", "meal_id", "name", "calories", "protein", "carbs", "fat", "confidence"} == set(
        food_items.columns.keys()
    )
    assert food_items.c.confidence.nullable is True
    meal_fk = next(iter(food_items.c.meal_id.foreign_keys))
    assert meal_fk.column.table.name == "meals"
    assert meal_fk.ondelete == "CASCADE"


def test_goal_user_id_is_unique() -> None:
    goals = Base.metadata.tables["goals"]
    assert {"id", "user_id", "daily_calories", "protein_goal", "carb_goal", "fat_goal"} == set(
        goals.columns.keys()
    )
    assert goals.c.user_id.unique is True


def test_relationships_wired() -> None:
    assert Meal.food_items.property.mapper.class_ is FoodItem
    assert FoodItem.meal.property.mapper.class_ is Meal
    assert Meal.user.property.mapper.class_ is User
    assert Goal.user.property.mapper.class_ is User
