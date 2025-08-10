import streamlit
import pandas
import requests
from urllib.error import URLError

# Cache external data to avoid re-fetching on every rerun
@streamlit.cache_data(show_spinner=False)
def load_fruit_macros():
    df = pandas.read_csv(
        "https://uni-lab-files.s3.us-west-2.amazonaws.com/dabw/fruit_macros.txt"
    )
    return df.set_index("Fruit")

# Reuse an HTTP session to keep connections warm
@streamlit.cache_resource(show_spinner=False)
def get_http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "streamlit-app/1.0"})
    return session

# Cache API responses by fruit to eliminate duplicate network calls during a session
@streamlit.cache_data(show_spinner=False, ttl=3600)
def get_fruityvice_data(this_fruit_choice: str):
    response = get_http_session().get(
        "https://fruityvice.com/api/fruit/" + this_fruit_choice, timeout=10
    )
    response.raise_for_status()
    return pandas.json_normalize(response.json())

# Cache the Snowflake connection as a resource to avoid reconnecting repeatedly
@streamlit.cache_resource(show_spinner=False)
def get_snowflake_connection():
    import snowflake.connector  # lazy import to reduce cold-start cost when Snowflake is unused

    return snowflake.connector.connect(**streamlit.secrets["snowflake"])


def get_fruit_load_list():
    with get_snowflake_connection().cursor() as my_cur:
        my_cur.execute("SELECT * from fruit_load_list")
        return my_cur.fetchall()


def insert_row_snowflake(new_fruit: str):
    with get_snowflake_connection().cursor() as my_cur:
        my_cur.execute("insert into fruit_load_list values('" + new_fruit + "')")
        return "Thanks for adding " + new_fruit


# UI
streamlit.title("My Parents new healthy Diner")
streamlit.header("Breakfast Menu")
streamlit.text("Omega 3 & Blueberry Oatmeal")
streamlit.text(" 🥗 Kale, Spinach & Rocket Smoothie")
streamlit.text("Hard-Boiled Free-Range Egg")

# Fruit picker and table (cached data)
my_fruit_list = load_fruit_macros()
fruits_selected = streamlit.multiselect(
    "Pick some fruits:", list(my_fruit_list.index), ["Avocado", "Strawberries"]
)
fruits_to_show = my_fruit_list.loc[fruits_selected]
streamlit.dataframe(fruits_to_show)

# Fruityvice section
streamlit.header("Fruity vice Fruit advice")
try:
    fruit_choice = streamlit.text_input(
        "What fruit would you like information about?"
    )
    if not fruit_choice:
        streamlit.error("Please select fruit to get information")
    else:
        back_from_function = get_fruityvice_data(fruit_choice)
        streamlit.dataframe(back_from_function)
except requests.exceptions.RequestException:
    streamlit.error("There was an error fetching data from Fruityvice.")
except URLError:
    # Keep compatibility with environments that might still raise URLError
    streamlit.error("Network error occurred.")

# Snowflake-backed features
streamlit.header("View our Fruit List:")
if "snowflake" in streamlit.secrets:
    if streamlit.button("Get Fruit List"):
        my_data_rows = get_fruit_load_list()
        streamlit.dataframe(my_data_rows)

    add_my_fruit = streamlit.text_input("What fruit would you like to add?")
    if streamlit.button("Add your favourites") and add_my_fruit:
        back_from_function = insert_row_snowflake(add_my_fruit)
        streamlit.text(back_from_function)
else:
    streamlit.info(
        "Snowflake features are disabled because Snowflake secrets are not configured."
    )

