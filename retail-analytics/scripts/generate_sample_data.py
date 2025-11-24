#!/usr/bin/env python3
"""
Generate sample retail data for the datacube
Creates realistic parquet files for all dimension and fact tables
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Base directory for data
DATA_DIR = Path(__file__).parent.parent / "data"

def create_directories():
    """Create all necessary data directories"""
    dirs = [
        "dim_product", "dim_store", "dim_dc", "dim_channel", 
        "dim_supplier", "dim_date",
        "bridge_dc_store_service", "bridge_store_catchment",
        "fact_pos_daily", "fact_inventory_daily_dc", 
        "fact_marketing_daily", "fact_merch_daily",
        "fact_procurement_po_daily", "fact_procurement_norms"
    ]
    for dir_name in dirs:
        (DATA_DIR / dir_name).mkdir(parents=True, exist_ok=True)
    print(f"✅ Created data directories in {DATA_DIR}")

def generate_dim_product():
    """Generate product dimension data"""
    products = []
    sku_id = 1
    
    categories = [
        (1, "Electronics", 1, "Technology"),
        (2, "Clothing", 2, "Apparel"),
        (3, "Home & Garden", 3, "Home"),
        (4, "Sports", 4, "Outdoor"),
        (5, "Food & Beverage", 5, "Grocery")
    ]
    
    brands = ["BrandA", "BrandB", "BrandC", "BrandD", "BrandE"]
    
    for cat_id, cat_name, dept_id, dept_name in categories:
        for i in range(20):  # 20 SKUs per category
            products.append({
                "sku_id": sku_id,
                "product_id": (sku_id - 1) // 4 + 1,  # Group SKUs into products
                "product_name": f"Product {sku_id}",
                "category_id": cat_id,
                "category_name": cat_name,
                "department_id": dept_id,
                "department_name": dept_name,
                "brand": np.random.choice(brands),
                "upc": f"UPC{sku_id:06d}"
            })
            sku_id += 1
    
    df = pd.DataFrame(products)
    df.to_parquet(DATA_DIR / "dim_product" / "products.parquet", index=False)
    print(f"✅ Generated {len(df)} products")
    return df

def generate_dim_store():
    """Generate store dimension data"""
    stores = []
    store_id = 1
    
    regions = [
        (1, "North Region"),
        (2, "South Region"),
        (3, "East Region"),
        (4, "West Region"),
        (5, "Central Region")
    ]
    
    cities = {
        1: ["New York", "Boston", "Philadelphia"],
        2: ["Atlanta", "Miami", "Charlotte"],
        3: ["Chicago", "Detroit", "Cleveland"],
        4: ["Los Angeles", "San Francisco", "Seattle"],
        5: ["Dallas", "Houston", "Denver"]
    }
    
    for region_id, region_name in regions:
        for city in cities[region_id]:
            for i in range(3):  # 3 stores per city
                stores.append({
                    "store_id": store_id,
                    "store_name": f"{city} Store {i+1}",
                    "city": city,
                    "state": "NY" if region_id == 1 else "CA" if region_id == 4 else "TX",
                    "postal_code": f"{10000 + store_id}",
                    "region_id": region_id,
                    "region_name": region_name,
                    "catchment_id": region_id,  # Simplified: catchment = region
                    "latitude": 40.0 + np.random.uniform(-5, 5),
                    "longitude": -75.0 + np.random.uniform(-10, 10)
                })
                store_id += 1
    
    df = pd.DataFrame(stores)
    df.to_parquet(DATA_DIR / "dim_store" / "stores.parquet", index=False)
    print(f"✅ Generated {len(df)} stores")
    return df

def generate_dim_dc():
    """Generate distribution center dimension data"""
    dcs = []
    for i in range(1, 6):
        dcs.append({
            "dc_id": i,
            "dc_name": f"DC {i}",
            "region_id": i,
            "region_name": f"Region {i}"
        })
    
    df = pd.DataFrame(dcs)
    df.to_parquet(DATA_DIR / "dim_dc" / "dcs.parquet", index=False)
    print(f"✅ Generated {len(df)} distribution centers")
    return df

def generate_dim_channel():
    """Generate channel dimension data"""
    channels = [
        {"channel_id": 1, "channel_name": "Online"},
        {"channel_id": 2, "channel_name": "TV"},
        {"channel_id": 3, "channel_name": "Radio"},
        {"channel_id": 4, "channel_name": "Print"},
        {"channel_id": 5, "channel_name": "Social Media"}
    ]
    
    df = pd.DataFrame(channels)
    df.to_parquet(DATA_DIR / "dim_channel" / "channels.parquet", index=False)
    print(f"✅ Generated {len(df)} channels")
    return df

def generate_dim_supplier():
    """Generate supplier dimension data"""
    suppliers = []
    for i in range(1, 11):
        suppliers.append({
            "supplier_id": i,
            "supplier_name": f"Supplier {i}",
            "incoterm": np.random.choice(["FOB", "CIF", "EXW"]),
            "currency": np.random.choice(["USD", "EUR", "GBP"])
        })
    
    df = pd.DataFrame(suppliers)
    df.to_parquet(DATA_DIR / "dim_supplier" / "suppliers.parquet", index=False)
    print(f"✅ Generated {len(df)} suppliers")
    return df

def generate_dim_date(start_date="2024-01-01", end_date="2024-12-31"):
    """Generate date dimension data"""
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current <= end:
        week_start = current - timedelta(days=current.weekday())
        month_start = current.replace(day=1)
        quarter = (current.month - 1) // 3 + 1
        quarter_start = datetime(current.year, (quarter - 1) * 3 + 1, 1)
        
        dates.append({
            "date": current.date(),
            "week_start": week_start.date(),
            "month_start": month_start.date(),
            "quarter_start": quarter_start.date(),
            "year": current.year,
            "fiscal_week": f"FY{current.year}W{current.isocalendar()[1]:02d}",
            "fiscal_period": f"FY{current.year}Q{quarter}"
        })
        current += timedelta(days=1)
    
    df = pd.DataFrame(dates)
    df.to_parquet(DATA_DIR / "dim_date" / "dates.parquet", index=False)
    print(f"✅ Generated {len(df)} dates")
    return df

def generate_bridge_dc_store_service(stores_df, dcs_df):
    """Generate DC to Store service allocation bridge"""
    bridges = []
    for _, dc in dcs_df.iterrows():
        # Each DC serves stores in its region
        region_stores = stores_df[stores_df["region_id"] == dc["region_id"]]
        num_stores = len(region_stores)
        
        if num_stores > 0:
            # Distribute service share (should sum to ~1.0 per DC)
            shares = np.random.dirichlet(np.ones(num_stores))
            for idx, (_, store) in enumerate(region_stores.iterrows()):
                bridges.append({
                    "dc_id": dc["dc_id"],
                    "store_id": store["store_id"],
                    "service_share": shares[idx]
                })
    
    df = pd.DataFrame(bridges)
    df.to_parquet(DATA_DIR / "bridge_dc_store_service" / "bridge.parquet", index=False)
    print(f"✅ Generated {len(df)} DC-store allocations")
    return df

def generate_bridge_store_catchment(stores_df):
    """Generate Store to Catchment bridge"""
    bridges = []
    for _, store in stores_df.iterrows():
        bridges.append({
            "store_id": store["store_id"],
            "catchment_id": store["catchment_id"],
            "catchment_share": 1.0  # Simplified: one-to-one
        })
    
    df = pd.DataFrame(bridges)
    df.to_parquet(DATA_DIR / "bridge_store_catchment" / "bridge.parquet", index=False)
    print(f"✅ Generated {len(df)} store-catchment allocations")
    return df

def generate_fact_pos_daily(stores_df, products_df, dates_df):
    """Generate POS daily fact data"""
    facts = []
    
    # Generate data for last 90 days
    recent_dates = dates_df.tail(90)
    
    for _, date_row in recent_dates.iterrows():
        date = date_row["date"]
        # Sample 20% of store-SKU combinations per day
        for _ in range(100):  # ~100 transactions per day
            store = stores_df.sample(1).iloc[0]
            product = products_df.sample(1).iloc[0]
            
            units_sold = np.random.poisson(5)  # Average 5 units
            unit_price = np.random.uniform(10, 100)
            net_sales = units_sold * unit_price
            returns_units = np.random.poisson(0.5) if np.random.random() < 0.1 else 0
            discounts = net_sales * np.random.uniform(0, 0.15) if np.random.random() < 0.3 else 0
            
            facts.append({
                "date": date,
                "store_id": store["store_id"],
                "sku_id": product["sku_id"],
                "units_sold": int(units_sold),
                "net_sales": round(net_sales, 2),
                "returns_units": int(returns_units),
                "discounts": round(discounts, 2)
            })
    
    df = pd.DataFrame(facts)
    df.to_parquet(DATA_DIR / "fact_pos_daily" / "pos.parquet", index=False)
    print(f"✅ Generated {len(df)} POS transactions")
    return df

def generate_fact_inventory_daily_dc(dcs_df, products_df, dates_df):
    """Generate inventory daily fact data"""
    facts = []
    
    recent_dates = dates_df.tail(30)
    
    for _, date_row in recent_dates.iterrows():
        date = date_row["date"]
        for _, dc in dcs_df.iterrows():
            for _, product in products_df.sample(50).iterrows():  # 50 SKUs per DC
                facts.append({
                    "date": date,
                    "dc_id": dc["dc_id"],
                    "sku_id": product["sku_id"],
                    "on_hand": int(np.random.uniform(100, 5000)),
                    "on_order": int(np.random.uniform(0, 1000)),
                    "receipts": int(np.random.uniform(0, 500))
                })
    
    df = pd.DataFrame(facts)
    df.to_parquet(DATA_DIR / "fact_inventory_daily_dc" / "inventory.parquet", index=False)
    print(f"✅ Generated {len(df)} inventory records")
    return df

def generate_fact_marketing_daily(regions, channels_df, dates_df):
    """Generate marketing daily fact data"""
    facts = []
    
    recent_dates = dates_df.tail(60)
    
    for _, date_row in recent_dates.iterrows():
        date = date_row["date"]
        for region_id in range(1, 6):
            for _, channel in channels_df.iterrows():
                if np.random.random() < 0.7:  # 70% chance of marketing activity
                    facts.append({
                        "date": date,
                        "region_id": region_id,
                        "catchment_id": region_id,
                        "channel_id": channel["channel_id"],
                        "campaign_id": np.random.randint(1, 20),
                        "spend": round(np.random.uniform(100, 5000), 2),
                        "impressions": int(np.random.uniform(1000, 100000)),
                        "clicks": int(np.random.uniform(10, 1000)),
                        "attributed_orders": int(np.random.uniform(0, 50))
                    })
    
    df = pd.DataFrame(facts)
    df.to_parquet(DATA_DIR / "fact_marketing_daily" / "marketing.parquet", index=False)
    print(f"✅ Generated {len(df)} marketing records")
    return df

def generate_fact_merch_daily(stores_df, products_df, dates_df):
    """Generate merchandising daily fact data"""
    facts = []
    
    recent_dates = dates_df.tail(30)
    
    for _, date_row in recent_dates.iterrows():
        date = date_row["date"]
        for _, store in stores_df.iterrows():
            for _, product in products_df.sample(30).iterrows():  # 30 SKUs per store
                facts.append({
                    "date": date,
                    "store_id": store["store_id"],
                    "sku_id": product["sku_id"],
                    "assortment_status": np.random.choice(["Active", "Discontinued", "New"]),
                    "facings": int(np.random.uniform(1, 10)),
                    "shelf_area_sq_in": round(np.random.uniform(10, 100), 2),
                    "promo_depth_pct": round(np.random.uniform(0, 30), 2) if np.random.random() < 0.2 else 0,
                    "promo_flag": np.random.random() < 0.2
                })
    
    df = pd.DataFrame(facts)
    df.to_parquet(DATA_DIR / "fact_merch_daily" / "merch.parquet", index=False)
    print(f"✅ Generated {len(df)} merchandising records")
    return df

def generate_fact_procurement_po_daily(dcs_df, products_df, suppliers_df, dates_df):
    """Generate procurement PO daily fact data"""
    facts = []
    
    recent_dates = dates_df.tail(60)
    
    for _, date_row in recent_dates.iterrows():
        po_date = date_row["date"]
        # Generate 5-10 POs per day
        for _ in range(np.random.randint(5, 11)):
            dc = dcs_df.sample(1).iloc[0]
            product = products_df.sample(1).iloc[0]
            supplier = suppliers_df.sample(1).iloc[0]
            
            qty_ordered = int(np.random.uniform(100, 5000))
            unit_cost = round(np.random.uniform(5, 50), 2)
            lead_time = np.random.randint(7, 30)
            eta_date = po_date + timedelta(days=lead_time)
            
            facts.append({
                "po_date": po_date,
                "dc_id": dc["dc_id"],
                "sku_id": product["sku_id"],
                "supplier_id": supplier["supplier_id"],
                "qty_ordered": qty_ordered,
                "unit_cost": unit_cost,
                "eta_date": eta_date,
                "lead_time_days": lead_time
            })
    
    df = pd.DataFrame(facts)
    df.to_parquet(DATA_DIR / "fact_procurement_po_daily" / "procurement.parquet", index=False)
    print(f"✅ Generated {len(df)} procurement POs")
    return df

def generate_fact_procurement_norms(products_df, suppliers_df):
    """Generate procurement norms/standards"""
    norms = []
    
    for _, supplier in suppliers_df.iterrows():
        for _, product in products_df.sample(20).iterrows():  # 20 SKUs per supplier
            norms.append({
                "supplier_id": supplier["supplier_id"],
                "sku_id": product["sku_id"],
                "std_lead_time_days": np.random.randint(7, 30),
                "moq_units": int(np.random.uniform(100, 1000))
            })
    
    df = pd.DataFrame(norms)
    df.to_parquet(DATA_DIR / "fact_procurement_norms" / "norms.parquet", index=False)
    print(f"✅ Generated {len(df)} procurement norms")
    return df

def main():
    print("🚀 Generating sample retail data for datacube...\n")
    
    create_directories()
    
    # Generate dimensions
    products_df = generate_dim_product()
    stores_df = generate_dim_store()
    dcs_df = generate_dim_dc()
    channels_df = generate_dim_channel()
    suppliers_df = generate_dim_supplier()
    dates_df = generate_dim_date()
    
    # Generate bridges
    generate_bridge_dc_store_service(stores_df, dcs_df)
    generate_bridge_store_catchment(stores_df)
    
    # Generate facts
    generate_fact_pos_daily(stores_df, products_df, dates_df)
    generate_fact_inventory_daily_dc(dcs_df, products_df, dates_df)
    generate_fact_marketing_daily(range(1, 6), channels_df, dates_df)
    generate_fact_merch_daily(stores_df, products_df, dates_df)
    generate_fact_procurement_po_daily(dcs_df, products_df, suppliers_df, dates_df)
    generate_fact_procurement_norms(products_df, suppliers_df)
    
    print("\n✅ Sample data generation complete!")
    print(f"📁 Data files saved to: {DATA_DIR}")

if __name__ == "__main__":
    main()

