from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine
import pandas as pd
import pymongo
from pyecharts.charts import Scatter, Bar, Grid, Line
from pyecharts import options as opts
from pyecharts.globals import ThemeType
import os

app = Flask(__name__)

# ==========================================
# 1. Database connection settings (please make sure the password is correct)
# ==========================================
DB_USER = "postgres"
DB_PASS = "123"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "my_db1_9_2"

# Connect to PostgreSQL (used for Part 3 macro-level data)
pg_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
pg_engine = create_engine(pg_str)

# Connect to MongoDB (used for Part 2 micro-level reviews)
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["yelp_analysis_db"]
mongo_col = mongo_db["reviews"]


# ==========================================
# 2. Page routing logic
# ==========================================

@app.route('/')
def dashboard():
    """
    Home Dashboard:
    - Viewport 1: Macro market (SQL Data -> Pyecharts Scatter)
    - Viewport 2: Deep dive (Tabs)
    """

    # --- Part 1: Fetch SQL market share data ---
    try:
        sql = "SELECT * FROM chipotle_market_analysis WHERE region IS NOT NULL"
        df = pd.read_sql(sql, pg_engine)
    except Exception as e:
        print(f"Error reading SQL: {e}")
        df = pd.DataFrame(columns=['region', 'brand', 'review_share_pct', 'avg_stars'])

    # Define brand colors and region order
    brand_colors = {
        "Chipotle": "#91cc75",  # Green (Chipotle Theme)
        "Qdoba": "#73c0de",  # Light Blue
        "Moes": "#ee6666",  # Red
        "Baja Fresh": "#5470c6",  # Deep Blue
        "Freebirds": "#fac858"  # Yellow
    }
    regions = ["Northeast", "South", "West", "Midwest"]  # In the display order you want

    # -------------------------------------------------------
    # Chart 1: Market Share Bubble Chart (macro)
    # -------------------------------------------------------
    scatter = Scatter()
    scatter.add_xaxis(regions)

    if not df.empty:
        # Sort to ensure Chipotle is drawn last so its bubbles are not covered
        unique_brands = df['brand'].unique().tolist()
        sorted_brands = sorted(unique_brands, key=lambda x: 1 if x == 'Chipotle' else 0)

        for brand in sorted_brands:
            sub = df[df['brand'] == brand].set_index('region')
            y_data = []
            for r in regions:
                # If a brand has no data in a region, set value to 0
                val = float(sub.loc[r, 'review_share_pct']) if r in sub.index else 0.0
                y_data.append(val)

            # Styling logic: highlight Chipotle, keep others semi-transparent
            item_style = {"color": brand_colors.get(brand, "grey")}
            if brand == "Chipotle":
                item_style.update({
                    "borderColor": "black",
                    "borderWidth": 2,
                    "shadowBlur": 10,
                    "shadowColor": "rgba(0,0,0,0.5)",
                    "opacity": 1.0
                })
            else:
                item_style.update({"opacity": 0.6, "borderWidth": 0})

            scatter.add_yaxis(
                series_name=brand,
                y_axis=y_data,
                symbol_size=20,  # Base size; actual size controlled by VisualMap
                itemstyle_opts=item_style,
                label_opts=opts.LabelOpts(
                    is_show=True,
                    formatter="{@[1]}%",  # Only show value + percent sign
                    position="right",
                    color="black" if brand == "Chipotle" else "grey",
                    font_weight="bold" if brand == "Chipotle" else "normal"
                )
            )

    scatter.set_global_opts(
        title_opts=opts.TitleOpts(title="Market Share by Region", pos_left="2%"),
        legend_opts=opts.LegendOpts(pos_top="2%", pos_right="5%"),
        xaxis_opts=opts.AxisOpts(name="Region", type_="category", splitline_opts=opts.SplitLineOpts(is_show=True)),
        yaxis_opts=opts.AxisOpts(name="Review Share (%)", max_=100, splitline_opts=opts.SplitLineOpts(is_show=True)),
        # VisualMap controls bubble size
        visualmap_opts=opts.VisualMapOpts(
            type_="size",
            max_=100,
            range_size=[15, 80],
            pos_bottom="10%",
            pos_left="2%"
        ),
    )

    # -------------------------------------------------------
    # Chart 2: Average Ratings Bar Chart (left side of Tab 1)
    # -------------------------------------------------------
    bar = Bar()
    bar.add_xaxis(regions)

    if not df.empty:
        unique_brands = df['brand'].unique().tolist()
        sorted_brands = sorted(unique_brands, key=lambda x: 1 if x == 'Chipotle' else 0)

        for brand in sorted_brands:
            sub = df[df['brand'] == brand].set_index('region')
            y_data = []
            for r in regions:
                val = float(sub.loc[r, 'avg_stars']) if r in sub.index else 0.0
                y_data.append(val)

            item_style = {"color": brand_colors.get(brand, "grey")}
            # Only Chipotle has a border
            if brand == "Chipotle":
                item_style.update({"borderColor": "white", "borderWidth": 1})

            # Only Chipotle shows numeric labels
            is_show_label = True if brand == "Chipotle" else False

            bar.add_yaxis(
                series_name=brand,
                y_axis=y_data,
                itemstyle_opts=item_style,
                category_gap="40%",
                label_opts=opts.LabelOpts(
                    is_show=is_show_label,
                    position="top",
                    font_weight="bold",
                    color="white"  # Works with dark background
                )
            )

    bar.set_global_opts(
        legend_opts=opts.LegendOpts(pos_top="5%", pos_right="5%", textstyle_opts=opts.TextStyleOpts(color="white")),
        yaxis_opts=opts.AxisOpts(name="Rating (1-5)", max_=5),
        # Tooltip is set to axis here to easily compare brands within the same region
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow")
    )

    # -------------------------------------------------------
    # Chart 3: Sentiment Drivers (right side of Tab 1 - based on NLP results)
    # -------------------------------------------------------

    # Source: Positive Bigrams Analysis
    pos_data = [
        ("Fast Food", 0.0194),
        ("Love Chipotle", 0.0193),
        ("Burrito Bowl", 0.0185),
        ("Staff Friendly", 0.0142),
        ("Food Fresh", 0.0128),
        ("Good Food", 0.0116)
    ]

    # Source: Negative Bigrams Analysis (terms that help tell the story)
    neg_data = [
        ("Customer Service", 0.0152),
        ("Worst Chipotle", 0.0131),
        ("Sour Cream", 0.0092),  # Related to portion size / extra charge complaints
        ("Online Order", 0.0076),  # Related to digital operations issues
        ("Chips Stale", 0.0050),  # Related to quality control
        ("30 Minutes", 0.0049)  # Related to wait time / efficiency
    ]

    # Positive bar chart (left half)
    bar_pos = (
        Bar()
        .add_xaxis([x[0] for x in pos_data])
        .add_yaxis("TF-IDF Score", [x[1] for x in pos_data], category_gap="50%",
                   itemstyle_opts=opts.ItemStyleOpts(color="#91cc75"))
        .reversal_axis()
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Positive Drivers", pos_left="25%",
                                      title_textstyle_opts=opts.TextStyleOpts(color="white", font_size=14)),  # Move title slightly toward the center
            xaxis_opts=opts.AxisOpts(is_show=False),
            # Key tweak: pos_left="25%" leaves room for labels
            yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="white")),
            legend_opts=opts.LegendOpts(is_show=False)
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="insideLeft"))
    )

    # Negative bar chart (right half)
    bar_neg = (
        Bar()
        .add_xaxis([x[0] for x in neg_data])
        .add_yaxis("TF-IDF Score", [x[1] for x in neg_data], category_gap="50%",
                   itemstyle_opts=opts.ItemStyleOpts(color="#ee6666"))
        .reversal_axis()
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Negative Drivers", pos_right="25%",
                                      title_textstyle_opts=opts.TextStyleOpts(color="white", font_size=14)),
            xaxis_opts=opts.AxisOpts(is_show=False, is_inverse=True),
            # Key tweak: position="right" with no offset; use Grid pos_right to control
            yaxis_opts=opts.AxisOpts(position="right", axislabel_opts=opts.LabelOpts(color="white")),
            legend_opts=opts.LegendOpts(is_show=False)
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="insideRight"))
    )

    # Combined chart (Grid)
    grid = (
        Grid(init_opts=opts.InitOpts(width="100%", height="400px", theme="dark"))
        # Key tweak:
        # pos_left="25%" -> leave space on the left for labels
        # pos_right="55%" -> right boundary of left chart (stops in the middle)
        .add(bar_pos, grid_opts=opts.GridOpts(pos_left="25%", pos_right="52%"))

        # pos_left="55%" -> left boundary of right chart (starts from middle)
        # pos_right="25%" -> leave space on the right for labels
        .add(bar_neg, grid_opts=opts.GridOpts(pos_left="52%", pos_right="25%"))
    )

    # -------------------------------------------------------
    # Part 4: Trend Chart (simplified stable version)
    # -------------------------------------------------------
    try:
        # 1. Read CSV (same path as before)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, "merged(2).csv")

        df_all = pd.read_csv(csv_path)

        # 2. Aggregate by year, ensure sorted by year
        df_trend = (
            df_all.groupby("year", as_index=False)[["avg_sentiment", "Operating_margin_state"]]
            .mean()
            .sort_values("year")
        )

        years = df_trend["year"].astype(str).tolist()
        sentiment_trend = df_trend["avg_sentiment"].round(3).tolist()
        margin_trend = df_trend["Operating_margin_state"].round(3).tolist()

        # 3. Draw a dual-axis line chart (no longer embedded in Grid; first ensure it renders)
        line = (
            Line(
                init_opts=opts.InitOpts(
                    width="100%",  # Let it adapt to div width
                    height="360px",
                    theme=ThemeType.DARK,
                    bg_color="transparent"
                )
            )
            .add_xaxis(years)

            # Left axis: Sentiment
            .add_yaxis(
                "Customer Sentiment",
                sentiment_trend,
                yaxis_index=0,
                is_smooth=True,
                symbol="circle",
                symbol_size=8,
                itemstyle_opts=opts.ItemStyleOpts(color="#91cc75"),
                label_opts=opts.LabelOpts(is_show=False),
            )

            # Right axis: Margin
            .add_yaxis(
                "Operating Margin",
                margin_trend,
                yaxis_index=1,
                is_smooth=True,
                symbol="circle",
                symbol_size=8,
                itemstyle_opts=opts.ItemStyleOpts(color="#fac858"),
                label_opts=opts.LabelOpts(is_show=False),
            )

            # Configure the second Y-axis on the right
            .extend_axis(
                yaxis=opts.AxisOpts(
                    name="Operating Margin",
                    type_="value",
                    position="right",
                    axisline_opts=opts.AxisLineOpts(
                        linestyle_opts=opts.LineStyleOpts(color="#fac858")
                    ),
                    axislabel_opts=opts.LabelOpts(formatter="{value}"),
                    splitline_opts=opts.SplitLineOpts(is_show=False),
                )
            )

            # Global options
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="Customer Sentiment vs. Operating Margin",
                    pos_left="center",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=16),
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="cross"
                ),
                legend_opts=opts.LegendOpts(
                    pos_top="5%",
                    textstyle_opts=opts.TextStyleOpts(color="white")
                ),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    boundary_gap=False,
                    axisline_opts=opts.AxisLineOpts(
                        linestyle_opts=opts.LineStyleOpts(color="#CCCCCC")
                    )
                ),
                yaxis_opts=opts.AxisOpts(
                    name="Sentiment",
                    type_="value",
                    position="left",
                    min_=-0.15,
                    max_=0.35,
                    axisline_opts=opts.AxisLineOpts(
                        linestyle_opts=opts.LineStyleOpts(color="#91cc75")
                    ),
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True,
                        linestyle_opts=opts.LineStyleOpts(opacity=0.2)
                    ),
                ),
            )
        )

        # 4. Export this chart's options directly (no extra Grid wrapper)
        trend_options = line.dump_options_with_quotes()
        print("Trend Chart 生成成功")

    except Exception as e:
        import traceback
        print(f"Trend Chart Error: {e}")
        traceback.print_exc()
        trend_options = "{}"

        # 3. Use Grid to adjust margins (to avoid labels being cut off)
        grid_chart = (
            Grid(init_opts=opts.InitOpts(theme=ThemeType.DARK, bg_color="transparent"))
            .add(
                line,
                grid_opts=opts.GridOpts(
                    pos_left="10%",  # Left margin
                    pos_right="10%",  # Right margin
                    pos_top="15%",  # Top margin leaves room for MarkArea text
                    pos_bottom="15%"  # Bottom margin leaves room for legend
                )
            )
        )

        trend_options = grid_chart.dump_options_with_quotes()
        print("Trend Chart 生成成功")

    except Exception as e:
        import traceback
        print(f"Trend Chart Error: {e}")
        traceback.print_exc()
        trend_options = "{}"

    return render_template(
        "dashboard.html",
        scatter_options=scatter.dump_options_with_quotes(),
        bar_options=bar.dump_options_with_quotes(),
        sentiment_options=grid.dump_options_with_quotes(),
        trend_options=trend_options
    )


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    """
    Review details page: read and filter reviews from MongoDB
    """
    selected_brand = request.args.get('brand', 'Chipotle')
    selected_stars = request.args.get('stars', 'All')

    query = {"brand": selected_brand}

    if selected_stars != 'All':
        # Convert star rating filter
        if selected_stars == '5':
            query["stars"] = 5.0
        elif selected_stars == '4':
            query["stars"] = 4.0
        elif selected_stars == '1':  # Negative usually 1 or 2
            query["stars"] = {"$lte": 2.0}
        else:
            query["stars"] = float(selected_stars)

    # Get the latest 100 reviews
    results = list(mongo_col.find(query).sort("date", -1).limit(100))

    return render_template("reviews.html",
                           reviews=results,
                           selected_brand=selected_brand,
                           selected_stars=selected_stars)

@app.route('/api/reviews', methods=['GET'])
def api_reviews():
    """
    JSON API:
    Return filtered review data from MongoDB for programmatic / visualization usage.
    Example:
      /api/reviews?brand=Chipotle&stars=5&limit=50
    """
    # 1. Read query parameters
    brand = request.args.get('brand', 'Chipotle')
    stars = request.args.get('stars', 'All')
    limit = request.args.get('limit', 100, type=int)

    # Put an upper limit to avoid dumping thousands of records at once
    limit = max(1, min(limit, 500))

    # 2. Build query conditions (same logic as /reviews page)
    query = {"brand": brand}

    if stars != 'All':
        if stars == '5':
            query["stars"] = 5.0
        elif stars == '4':
            query["stars"] = 4.0
        elif stars == '1':  # negative: 1 or 2 stars
            query["stars"] = {"$lte": 2.0}
        else:
            try:
                query["stars"] = float(stars)
            except ValueError:
                pass  # Ignore invalid input and fall back to filtering only by brand

    # 3. Fetch data from MongoDB
    cursor = mongo_col.find(query).sort("date", -1).limit(limit)

    data = []
    for doc in cursor:
        # Convert ObjectId to string to avoid JSON errors
        doc['_id'] = str(doc['_id'])
        data.append(doc)

    # 4. Return JSON response
    return jsonify({
        "status": "ok",
        "count": len(data),
        "brand": brand,
        "stars_filter": stars,
        "data": data
    })

#http://127.0.0.1:5000/api/reviews?brand=Chipotle
#http://127.0.0.1:5000/api/reviews?brand=Qdoba&stars=5&limit=50
#http://127.0.0.1:5000/api/reviews?brand=Chipotle&stars=1

if __name__ == "__main__":
    app.run(debug=True)
