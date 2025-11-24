-- ============================================================================
-- Comprehensive Ontology Seed Data
-- Generated from: ontology seed.txt
-- Populates ontology_concepts, ontology_mappings, and ontology_shapes tables
-- ============================================================================

-- Start transaction
BEGIN;

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:Product', 'ex:ProductConceptScheme',
   'Product', ARRAY['SKU','Item'],
   'A sellable item or service in the manufacturer or retailer catalog.', NULL),


  ('ex:ProductIdentifierType', 'ex:ProductConceptScheme',
   'Product Identifier Type', ARRAY['ID Type'],
   'Type of identifier used to uniquely identify a product across systems.', 'ex:Product'),


  ('ex:ProductIdentifierType/GTIN', 'ex:ProductConceptScheme',
   'GTIN / UPC / EAN', ARRAY['UPC','EAN','Barcode'],
   'Global Trade Item Number and related barcode identifiers used as canonical product keys.', 'ex:ProductIdentifierType'),


  ('ex:ProductIdentifierType/ManufacturerSKU', 'ex:ProductConceptScheme',
   'Manufacturer SKU', ARRAY['Item Code','Internal SKU'],
   'Manufacturer-defined stock keeping unit code.', 'ex:ProductIdentifierType'),


  ('ex:ProductIdentifierType/RetailerSKU', 'ex:ProductConceptScheme',
   'Retailer SKU', ARRAY['Store SKU'],
   'Retailer-defined identifier used in POS and retail media logs.', 'ex:ProductIdentifierType'),


  ('ex:ProductIdentifierType/ASIN', 'ex:ProductConceptScheme',
   'ASIN', ARRAY['Amazon ASIN'],
   'Amazon Standard Identification Number used on marketplace and RMN.', 'ex:ProductIdentifierType')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:ProductHierarchy', 'ex:ProductConceptScheme',
   'Product Hierarchy', ARRAY['Merch Hierarchy'],
   'Standardized hierarchy for grouping products for reporting and targeting.', 'ex:Product'),


  ('ex:ProductHierarchy/Division', 'ex:ProductConceptScheme',
   'Division', ARRAY['Business Division'],
   'Top-level product division or business grouping.', 'ex:ProductHierarchy'),


  ('ex:ProductHierarchy/CategoryGroup', 'ex:ProductConceptScheme',
   'Category Group', ARRAY['Portfolio'],
   'Portfolio or category group within a division.', 'ex:ProductHierarchy'),


  ('ex:ProductHierarchy/Department', 'ex:ProductConceptScheme',
   'Department', ARRAY['Department'],
   'Department such as Food, Home Care, Beauty.', 'ex:ProductHierarchy'),


  ('ex:ProductHierarchy/Supercategory', 'ex:ProductConceptScheme',
   'Supercategory', ARRAY['Macro Category'],
   'Supercategory such as Beverages, Snacks, Personal Care.', 'ex:ProductHierarchy'),


  ('ex:ProductHierarchy/Category', 'ex:ProductConceptScheme',
   'Category', ARRAY['Product Category'],
   'Mid-level product category such as Soft Drinks, Yogurt, Shampoo.', 'ex:ProductHierarchy'),


  ('ex:ProductHierarchy/Subcategory', 'ex:ProductConceptScheme',
   'Subcategory', ARRAY['Sub Category'],
   'Subcategory such as Cola, Energy Drinks, Sparkling Water.', 'ex:ProductHierarchy'),


  ('ex:ProductHierarchy/Segment', 'ex:ProductConceptScheme',
   'Segment', ARRAY['Consumer Segment'],
   'Finer-grain segment such as Regular Cola vs Diet Cola.', 'ex:ProductHierarchy'),


  ('ex:ProductHierarchy/Subsegment', 'ex:ProductConceptScheme',
   'Subsegment', ARRAY['Micro Segment'],
   'Micro-segment for niche groupings or shopper missions.', 'ex:ProductHierarchy')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:ProductCategory/Beverages', 'ex:ProductCategoryScheme',
   'Beverages', ARRAY['Drinks'],
   'Top-level product category for all beverage products.', 'ex:ProductHierarchy/Supercategory'),


  ('ex:ProductCategory/Beverages/SoftDrinks', 'ex:ProductCategoryScheme',
   'Soft Drinks', ARRAY['Carbonated Soft Drinks','CSD'],
   'Non-alcoholic carbonated soft drinks.', 'ex:ProductCategory/Beverages'),


  ('ex:ProductCategory/Beverages/SoftDrinks/Cola', 'ex:ProductCategoryScheme',
   'Cola', ARRAY['Cola Drinks'],
   'Soft drinks with cola flavor profile.', 'ex:ProductCategory/Beverages/SoftDrinks')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:Brand', 'ex:ProductConceptScheme',
   'Brand', ARRAY['Consumer Brand'],
   'Consumer-facing brand used in communication and packaging.', 'ex:Product'),


  ('ex:CorporateBrand', 'ex:ProductConceptScheme',
   'Corporate Brand', ARRAY['House of Brands','Masterbrand'],
   'Corporate or master brand owning one or more consumer brands.', 'ex:Brand'),


  ('ex:SubBrand', 'ex:ProductConceptScheme',
   'Sub-brand', ARRAY['Variant Line'],
   'Sub-brand used to differentiate lines within a brand (e.g., Zero Sugar).', 'ex:Brand'),


  ('ex:CoBrand', 'ex:ProductConceptScheme',
   'Co-brand', ARRAY['Partner Brand'],
   'Partner or co-branded property appearing on pack or creative.', 'ex:Brand'),


  ('ex:FranchiseIP', 'ex:ProductConceptScheme',
   'Franchise / IP', ARRAY['Licensed IP'],
   'Licensed intellectual property such as movies or characters.', 'ex:Brand'),


  ('ex:BrandRole', 'ex:ProductConceptScheme',
   'Brand Role', ARRAY['Portfolio Role'],
   'Role a brand plays in the portfolio (hero, support, entry, halo).', 'ex:Brand'),


  ('ex:BrandRole/Hero', 'ex:ProductConceptScheme',
   'Hero Brand', ARRAY['Lead Brand'],
   'Lead or flagship brand in the portfolio.', 'ex:BrandRole'),


  ('ex:BrandRole/Support', 'ex:ProductConceptScheme',
   'Support Brand', ARRAY['Supportive Brand'],
   'Brand that supports the hero brand in communication and shelf.', 'ex:BrandRole'),


  ('ex:BrandRole/Entry', 'ex:ProductConceptScheme',
   'Entry Brand', ARRAY['Entry Tier Brand'],
   'Entry price or trial-focused brand.', 'ex:BrandRole'),


  ('ex:BrandRole/Halo', 'ex:ProductConceptScheme',
   'Halo Brand', ARRAY['Halo Tier Brand'],
   'Brand used to elevate perception of the rest of the range.', 'ex:BrandRole'),


  ('ex:BrandTier', 'ex:ProductConceptScheme',
   'Brand Tier', ARRAY['Price Tier'],
   'Relative value positioning of the brand.', 'ex:Brand'),


  ('ex:BrandTier/Premium', 'ex:ProductConceptScheme',
   'Premium', ARRAY['High End'],
   'Premium priced and positioned brand tier.', 'ex:BrandTier'),


  ('ex:BrandTier/Mainstream', 'ex:ProductConceptScheme',
   'Mainstream', ARRAY['Mid Tier'],
   'Mainstream or mid-tier brand tier.', 'ex:BrandTier'),


  ('ex:BrandTier/Value', 'ex:ProductConceptScheme',
   'Value', ARRAY['Economy'],
   'Value or economy brand tier.', 'ex:BrandTier')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:ProductForm', 'ex:ProductConceptScheme',
   'Product Form', ARRAY['Physical Form'],
   'Physical form in which the product is delivered.', 'ex:Product'),


  ('ex:ProductForm/Liquid', 'ex:ProductConceptScheme',
   'Liquid', ARRAY[]::text[],
   'Liquid form product.', 'ex:ProductForm'),


  ('ex:ProductForm/Powder', 'ex:ProductConceptScheme',
   'Powder', ARRAY[]::text[],
   'Powder or granule product.', 'ex:ProductForm'),


  ('ex:ProductForm/Bar', 'ex:ProductConceptScheme',
   'Bar', ARRAY['Snack Bar'],
   'Bar format product (e.g., cereal bar).', 'ex:ProductForm'),


  ('ex:UsageType', 'ex:ProductConceptScheme',
   'Usage Type', ARRAY['Preparation Type'],
   'How the product is used (ready-to-drink, concentrate, mix-in).', 'ex:Product'),


  ('ex:UsageType/ReadyToDrink', 'ex:ProductConceptScheme',
   'Ready-to-Drink', ARRAY['RTD'],
   'Product is consumed as sold, without preparation.', 'ex:UsageType'),


  ('ex:UsageType/Concentrate', 'ex:ProductConceptScheme',
   'Concentrate', ARRAY['Syrup'],
   'Product intended to be diluted before use.', 'ex:UsageType'),


  ('ex:Application', 'ex:ProductConceptScheme',
   'Application', ARRAY['Use Case'],
   'Primary use case such as snacking, breakfast, cleaning.', 'ex:Product'),


  ('ex:BenefitTerritory', 'ex:ProductConceptScheme',
   'Benefit Territory', ARRAY['Benefit Platform'],
   'Functional or emotional benefit platform (hydration, energy, whitening).', 'ex:Product'),


  ('ex:NeedState', 'ex:ProductConceptScheme',
   'Need State', ARRAY['Shopper Need'],
   'Shopper need being fulfilled (on-the-go hunger, family sharing, self-care).', 'ex:Product'),


  ('ex:Occasion', 'ex:ProductConceptScheme',
   'Occasion', ARRAY['Consumption Occasion'],
   'Occasions such as breakfast, movie night, holiday, party.', 'ex:Product'),


  ('ex:Occasion/Breakfast', 'ex:ProductConceptScheme',
   'Breakfast', ARRAY['Morning Meal'],
   'Breakfast eating or drinking occasion.', 'ex:Occasion'),


  ('ex:Occasion/MovieNight', 'ex:ProductConceptScheme',
   'Movie Night', ARRAY['Cinema at Home'],
   'Movie or TV viewing occasion.', 'ex:Occasion')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:PackType', 'ex:ProductConceptScheme',
   'Pack Type', ARRAY['Primary Pack Type'],
   'Primary packaging type such as bottle, can, pouch.', 'ex:Product'),


  ('ex:PackType/Bottle', 'ex:ProductConceptScheme',
   'Bottle', ARRAY[]::text[],
   'Rigid bottle pack, typically plastic or glass.', 'ex:PackType'),


  ('ex:PackType/Can', 'ex:ProductConceptScheme',
   'Can', ARRAY['Can Pack'],
   'Metal can packaging.', 'ex:PackType'),


  ('ex:PackType/Pouch', 'ex:ProductConceptScheme',
   'Pouch', ARRAY['Pouch Pack'],
   'Flexible pouch packaging.', 'ex:PackType'),


  ('ex:PackConfiguration', 'ex:ProductConceptScheme',
   'Pack Configuration', ARRAY['Pack Config'],
   'Configuration such as single, multipack, variety pack.', 'ex:Product'),


  ('ex:PackConfiguration/Single', 'ex:ProductConceptScheme',
   'Single Pack', ARRAY['Single Unit'],
   'Single consumer unit per pack.', 'ex:PackConfiguration'),


  ('ex:PackConfiguration/Multipack', 'ex:ProductConceptScheme',
   'Multipack', ARRAY['Multi Pack'],
   'Multipack with multiple identical units.', 'ex:PackConfiguration'),


  ('ex:PackConfiguration/VarietyPack', 'ex:ProductConceptScheme',
   'Variety Pack', ARRAY['Assortment Pack'],
   'Multipack with mixed variants or flavors.', 'ex:PackConfiguration'),


  ('ex:PackageMaterial', 'ex:ProductConceptScheme',
   'Package Material', ARRAY['Material'],
   'Material of primary packaging (plastic, glass, aluminum, cardboard).', 'ex:Product'),


  ('ex:PackageMaterial/Plastic', 'ex:ProductConceptScheme',
   'Plastic', ARRAY[]::text[],
   'Plastic packaging material.', 'ex:PackageMaterial'),


  ('ex:PackageMaterial/Glass', 'ex:ProductConceptScheme',
   'Glass', ARRAY[]::text[],
   'Glass packaging material.', 'ex:PackageMaterial'),


  ('ex:PackageMaterial/Aluminum', 'ex:ProductConceptScheme',
   'Aluminum', ARRAY['Aluminium'],
   'Aluminum packaging material.', 'ex:PackageMaterial'),


  ('ex:ClosureType', 'ex:ProductConceptScheme',
   'Closure Type', ARRAY['Cap Type'],
   'Closure such as screw cap, flip-top, pump.', 'ex:Product'),


  ('ex:SustainabilityMarker', 'ex:ProductConceptScheme',
   'Sustainability Marker', ARRAY['Recyclability Marker'],
   'Labels indicating recyclability or sustainability attributes.', 'ex:Product')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:UnitOfMeasure', 'ex:ProductConceptScheme',
   'Unit of Measure', ARRAY['UOM'],
   'Unit for net content (ml, L, g, kg, oz, fl oz).', 'ex:Product'),


  ('ex:UnitOfMeasure/ml', 'ex:ProductConceptScheme',
   'Millilitre', ARRAY['ml'],
   'Millilitre unit of measure.', 'ex:UnitOfMeasure'),


  ('ex:UnitOfMeasure/L', 'ex:ProductConceptScheme',
   'Litre', ARRAY['L'],
   'Litre unit of measure.', 'ex:UnitOfMeasure'),


  ('ex:UnitOfMeasure/g', 'ex:ProductConceptScheme',
   'Gram', ARRAY['g'],
   'Gram unit of measure.', 'ex:UnitOfMeasure'),


  ('ex:SizeBand', 'ex:ProductConceptScheme',
   'Size Band', ARRAY['Pack Size Band'],
   'Size band such as small, medium, large, XL.', 'ex:Product'),


  ('ex:PriceTier', 'ex:ProductConceptScheme',
   'Price Tier', ARRAY['Price Positioning'],
   'Regular price positioning such as value, mainstream, premium.', 'ex:Product'),


  ('ex:PricePackArchitectureSegment', 'ex:ProductConceptScheme',
   'Price Pack Architecture Segment', ARRAY['PPA Segment'],
   'Good / better / best style price-pack architecture.', 'ex:Product')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:DietaryAttribute', 'ex:ProductConceptScheme',
   'Dietary Attribute', ARRAY['Diet Tag'],
   'Dietary attributes such as vegan, vegetarian, gluten-free, kosher, halal.', 'ex:Product'),


  ('ex:DietaryAttribute/Vegan', 'ex:ProductConceptScheme',
   'Vegan', ARRAY[]::text[],
   'Product contains no animal-derived ingredients.', 'ex:DietaryAttribute'),


  ('ex:DietaryAttribute/GlutenFree', 'ex:ProductConceptScheme',
   'Gluten-free', ARRAY['GF'],
   'Product is formulated to be gluten-free.', 'ex:DietaryAttribute'),


  ('ex:AllergyTag', 'ex:ProductConceptScheme',
   'Allergy Tag', ARRAY['Allergen Tag'],
   'Allergen presence or absence markers (contains nuts, dairy-free, etc.).', 'ex:Product'),


  ('ex:CertificationTag', 'ex:ProductConceptScheme',
   'Certification Tag', ARRAY['Certification'],
   'Third-party certifications such as organic, fair trade.', 'ex:Product'),


  ('ex:AgeRestrictionFlag', 'ex:ProductConceptScheme',
   'Age Restriction Flag', ARRAY['Age Flag'],
   'Flag for products restricted to adults or specific ages.', 'ex:Product'),


  ('ex:RegulatoryClass', 'ex:ProductConceptScheme',
   'Regulatory Class', ARRAY['Reg Class'],
   'Country or region-specific regulatory class.', 'ex:Product')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:CustomerSegment', 'ex:AudienceConceptScheme',
   'Customer Segment', ARRAY['Shopper Segment'],
   'Shopper or household segment used for CRM and RMN targeting.', NULL),


  ('ex:SegmentFamily', 'ex:AudienceConceptScheme',
   'Segment Family', ARRAY['Segment Group'],
   'Groupings such as Lapsed, New-to-brand, Heavy buyers.', 'ex:CustomerSegment'),


  ('ex:LifecycleStage', 'ex:AudienceConceptScheme',
   'Lifecycle Stage', ARRAY['Customer Lifecycle Stage'],
   'Prospect, new, active, lapsed, reactivated.', 'ex:CustomerSegment'),


  ('ex:ValueTier', 'ex:AudienceConceptScheme',
   'Value Tier', ARRAY['Customer Value Tier'],
   'Low / medium / high customer value bands.', 'ex:CustomerSegment'),


  ('ex:FrequencyTier', 'ex:AudienceConceptScheme',
   'Frequency Tier', ARRAY['Buyer Frequency Tier'],
   'Light / medium / heavy buyer frequency bands.', 'ex:CustomerSegment'),


  ('ex:BasketRole', 'ex:AudienceConceptScheme',
   'Basket Role', ARRAY['Trip Role'],
   'Role of a shopper in the household or basket (main buyer, top-up buyer).', 'ex:CustomerSegment'),


  ('ex:ChannelPreference', 'ex:AudienceConceptScheme',
   'Channel Preference', ARRAY['Primary Channel Preference'],
   'Preferred channel such as in-store, online, click & collect, delivery.', 'ex:CustomerSegment'),


  ('ex:PriceSensitivityTier', 'ex:AudienceConceptScheme',
   'Price Sensitivity Tier', ARRAY['Price Elasticity Tier'],
   'Relative price sensitivity of a shopper or segment.', 'ex:CustomerSegment'),


  ('ex:BrandLoyaltyLevel', 'ex:AudienceConceptScheme',
   'Brand Loyalty Level', ARRAY['Loyalty Level'],
   'Exclusive, repertoire, or switching behavior.', 'ex:CustomerSegment'),


  ('ex:CrossCategoryAffinity', 'ex:AudienceConceptScheme',
   'Cross-category Affinity', ARRAY['Affinity'],
   'Affinities between categories, e.g., cola plus salty snacks.', 'ex:CustomerSegment'),


  ('ex:HouseholdLifeStage', 'ex:AudienceConceptScheme',
   'Household Life Stage', ARRAY['HH Life Stage'],
   'Young singles, families with kids, empty nesters, etc.', 'ex:CustomerSegment'),


  ('ex:HouseholdSizeBand', 'ex:AudienceConceptScheme',
   'Household Size Band', ARRAY['HH Size'],
   'Bucketed household size (1, 2, 3-4, 5+).', 'ex:CustomerSegment'),


  ('ex:IncomeBand', 'ex:AudienceConceptScheme',
   'Income Band', ARRAY['Affluence Segment'],
   'Income or affluence band segments.', 'ex:CustomerSegment'),


  ('ex:Urbanicity', 'ex:AudienceConceptScheme',
   'Urbanicity', ARRAY['Urbanicity Cluster'],
   'Urban, suburban, rural cluster codes.', 'ex:CustomerSegment'),


  ('ex:RegionCluster', 'ex:AudienceConceptScheme',
   'Region / Market Cluster', ARRAY['Region Cluster'],
   'Geo-based market clusters for targeting and reporting.', 'ex:CustomerSegment'),


  ('ex:LifestyleSegment', 'ex:AudienceConceptScheme',
   'Lifestyle Segment', ARRAY['Persona'],
   'Psychographic or lifestyle personas (e.g., busy professionals).', 'ex:CustomerSegment')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:Campaign', 'ex:CampaignConceptScheme',
   'Campaign', ARRAY['Ad Campaign','Marketing Campaign'],
   'A planned set of advertising tactics with a defined objective, budget, and time window.', NULL),


  ('ex:CampaignType', 'ex:CampaignConceptScheme',
   'Campaign Type', ARRAY['Objective Type'],
   'High-level role such as brand-building, trade support, seasonal, always-on.', 'ex:Campaign'),


  ('ex:FunnelStage', 'ex:CampaignConceptScheme',
   'Funnel Stage', ARRAY['Journey Stage'],
   'Stage in the marketing funnel (awareness, consideration, conversion, loyalty).', 'ex:Campaign'),


  ('ex:FunnelStage/Awareness', 'ex:CampaignConceptScheme',
   'Awareness', ARRAY[]::text[],
   'Top-of-funnel awareness stage.', 'ex:FunnelStage'),


  ('ex:FunnelStage/Consideration', 'ex:CampaignConceptScheme',
   'Consideration', ARRAY[]::text[],
   'Mid-funnel consideration stage.', 'ex:FunnelStage'),


  ('ex:FunnelStage/Conversion', 'ex:CampaignConceptScheme',
   'Conversion', ARRAY['Purchase'],
   'Lower-funnel conversion stage.', 'ex:FunnelStage'),


  ('ex:FunnelStage/Loyalty', 'ex:CampaignConceptScheme',
   'Loyalty', ARRAY[]::text[],
   'Post-purchase loyalty and retention stage.', 'ex:FunnelStage'),


  ('ex:CampaignObjective', 'ex:CampaignConceptScheme',
   'Primary Campaign Objective', ARRAY['Primary Objective'],
   'Primary objective such as reach, traffic, sales, new-to-brand, trial.', 'ex:Campaign'),


  ('ex:StrategyTheme', 'ex:CampaignConceptScheme',
   'Strategy Theme', ARRAY['Strategic Theme'],
   'Strategy themes such as penetration, premiumization, trade-up, retention.', 'ex:Campaign'),


  ('ex:TacticFamily', 'ex:CampaignConceptScheme',
   'Tactic Family', ARRAY['Tactic Type'],
   'Tactic families such as search, sponsored product, display, video, audio.', 'ex:Campaign'),


  ('ex:PlacementEnvironment', 'ex:CampaignConceptScheme',
   'Placement Environment', ARRAY['Environment'],
   'Environment such as onsite, offsite, social extension, email.', 'ex:Campaign'),


  ('ex:PlacementLocation', 'ex:CampaignConceptScheme',
   'Placement Location', ARRAY['Page Location'],
   'Placement location such as homepage, search results, category page, cart, checkout.', 'ex:Campaign'),


  ('ex:BuyingType', 'ex:CampaignConceptScheme',
   'Buying Type', ARRAY['Deal Type'],
   'Auction, fixed fee, sponsorship, or other buying mechanisms.', 'ex:Campaign'),


  ('ex:OptimizationGoal', 'ex:CampaignConceptScheme',
   'Optimization Goal', ARRAY['Bid Strategy Goal'],
   'Optimization goal such as impressions, clicks, conversions, ROAS, share of voice.', 'ex:Campaign'),


  ('ex:TargetProductFocus', 'ex:CampaignConceptScheme',
   'Target Product Focus', ARRAY['Product Focus'],
   'Focus such as single SKU, line, brand, multi-brand, innovation vs base.', 'ex:Campaign'),


  ('ex:CreativeType', 'ex:CampaignConceptScheme',
   'Creative Type', ARRAY['Ad Format'],
   'Creative formats such as static image, carousel, video, shoppable video.', 'ex:Campaign'),


  ('ex:CreativeMessage', 'ex:CampaignConceptScheme',
   'Creative Message', ARRAY['Message Theme'],
   'Creative message themes (value, quality, taste, convenience, health).', 'ex:Campaign'),


  ('ex:OfferType', 'ex:CampaignConceptScheme',
   'Offer vs Non-offer', ARRAY['Offer Classification'],
   'Whether creative is promo-led or equity-led.', 'ex:Campaign'),


  ('ex:LanguageLocale', 'ex:CampaignConceptScheme',
   'Language / Locale', ARRAY['Locale'],
   'Language and locale for creatives and campaigns.', 'ex:Campaign')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:RetailerGroup', 'ex:RetailConceptScheme',
   'Retailer Group', ARRAY['Retailer Parent'],
   'Corporate parent group of one or more retail banners.', NULL),


  ('ex:RetailBanner', 'ex:RetailConceptScheme',
   'Retail Banner', ARRAY['Banner','Fascia'],
   'Consumer-facing retail banner or fascia.', 'ex:RetailerGroup'),


  ('ex:StoreFormat', 'ex:RetailConceptScheme',
   'Store Format', ARRAY['Format'],
   'Format such as hypermarket, supermarket, convenience, drug, club, discounter.', 'ex:RetailBanner'),


  ('ex:ChannelType', 'ex:RetailConceptScheme',
   'Channel Type', ARRAY['Trade Channel'],
   'Trade channel such as grocery, mass, club, drug, online pure-play, quick commerce.', NULL),


  ('ex:AccountSegment', 'ex:RetailConceptScheme',
   'Account Segment', ARRAY['Account Tier'],
   'Account tiers such as strategic, key, focus, long tail.', 'ex:RetailerGroup'),


  ('ex:SalesChannel', 'ex:RetailConceptScheme',
   'Sales Channel', ARRAY['Commerce Channel'],
   'Brick-and-mortar, ecommerce, marketplace, DTC.', NULL),


  ('ex:FulfillmentModel', 'ex:RetailConceptScheme',
   'Fulfillment Model', ARRAY['Fulfilment Model'],
   'Ship-to-home, pickup, delivery, in-store only, etc.', 'ex:SalesChannel'),


  ('ex:RetailMediaPropertyType', 'ex:RetailConceptScheme',
   'Retail Media Property Type', ARRAY['RMN Property Type'],
   'Property types such as search, display, sponsored listing, email, offsite extensions.', NULL),


  ('ex:RetailMediaPlatform', 'ex:RetailConceptScheme',
   'Retail Media Platform', ARRAY['RMN Platform'],
   'Specific retail media networks such as Walmart Connect or Amazon Ads.', 'ex:RetailMediaPropertyType')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:Store', 'ex:StoreConceptScheme',
   'Store', ARRAY['Outlet'],
   'Physical or virtual store location.', NULL),


  ('ex:StoreCluster', 'ex:StoreConceptScheme',
   'Store Cluster', ARRAY['Cluster'],
   'Cluster such as performance, affluence, or format clusters.', 'ex:Store'),


  ('ex:StoreRole', 'ex:StoreConceptScheme',
   'Store Role', ARRAY['Network Role'],
   'Flagship, neighborhood, outlet, pickup-only roles.', 'ex:Store'),


  ('ex:Market', 'ex:GeoConceptScheme',
   'Market', ARRAY['Sales Region'],
   'Market or sales territory used for planning.', NULL),


  ('ex:Country', 'ex:GeoConceptScheme',
   'Country', ARRAY[]::text[],
   'ISO-3166 country-level geography.', 'ex:Market'),


  ('ex:Region', 'ex:GeoConceptScheme',
   'Region / Territory', ARRAY['Region'],
   'State, province, or regional group.', 'ex:Market'),


  ('ex:TradeArea', 'ex:GeoConceptScheme',
   'Trade Area', ARRAY['DMA','Local Market'],
   'Trade area or DMA-level cluster.', 'ex:Market'),


  ('ex:GeoUrbanicity', 'ex:GeoConceptScheme',
   'Geographic Urbanicity', ARRAY['Geo Urbanicity'],
   'Urban, suburban, rural density classification.', 'ex:Market'),


  ('ex:AssortmentStatus', 'ex:StoreConceptScheme',
   'Listing Status', ARRAY['Assortment Status'],
   'Listed, delisted, temporary listing status.', 'ex:Store'),


  ('ex:DistributionTier', 'ex:StoreConceptScheme',
   'Distribution Tier', ARRAY['Distribution Level'],
   'Distribution tiers such as core, extended, limited.', 'ex:Store'),


  ('ex:SpaceAllocationBand', 'ex:StoreConceptScheme',
   'Space Allocation Band', ARRAY['Shelf Space Band'],
   'Space allocation such as share of shelf bands.', 'ex:Store')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:Promotion', 'ex:PromotionConceptScheme',
   'Promotion', ARRAY['Promo'],
   'Promotion or offer mechanics applied to products.', NULL),


  ('ex:PromoType', 'ex:PromotionConceptScheme',
   'Promotion Type', ARRAY['Promo Mechanic Type'],
   'Price off, multi-buy, BOGO, bundle, gift with purchase, loyalty points.', 'ex:Promotion'),


  ('ex:PromoMechanic', 'ex:PromotionConceptScheme',
   'Promotion Mechanic Detail', ARRAY['Mechanic Detail'],
   'Detailed description such as "buy 2 get 1 free" or "25% off".', 'ex:Promotion'),


  ('ex:PromoDepthBand', 'ex:PromotionConceptScheme',
   'Promotion Depth Band', ARRAY['Discount Depth Band'],
   'Bands of discount depth (0–10%, 10–20%, etc.).', 'ex:Promotion'),


  ('ex:PromoFrequencyBand', 'ex:PromotionConceptScheme',
   'Promotion Frequency Band', ARRAY['Promo Frequency'],
   'Always-on, frequent, occasional, rare.', 'ex:Promotion'),


  ('ex:PromoStackingType', 'ex:PromotionConceptScheme',
   'Promotion Stacking Type', ARRAY['Stacking Type'],
   'Single offer or multiple offers combined.', 'ex:Promotion'),


  ('ex:FeatureType', 'ex:PromotionConceptScheme',
   'Feature Type', ARRAY['Ad Feature Type'],
   'Circular, flyer, digital ad, email, app notification.', 'ex:Promotion'),


  ('ex:DisplayType', 'ex:PromotionConceptScheme',
   'Display Type', ARRAY['In-Store Display Type'],
   'Endcap, aisle, checkout, island, pallet, sidecap.', 'ex:Promotion'),


  ('ex:SecondaryPlacementType', 'ex:PromotionConceptScheme',
   'Secondary Placement Type', ARRAY['Secondary Placement'],
   'Secondary shelf, special stand, dump bin, etc.', 'ex:Promotion'),


  ('ex:LoyaltyPromoType', 'ex:PromotionConceptScheme',
   'Loyalty / Targeted Promo Type', ARRAY['Loyalty Offer Type'],
   'Points boost, targeted coupon, personalized offer.', 'ex:Promotion'),


  ('ex:TradeProgramType', 'ex:PromotionConceptScheme',
   'Trade Program Type', ARRAY['Trade Strategy'],
   'EDLP, hi-lo, trade activation, joint business plan initiative.', 'ex:Promotion'),


  ('ex:TradeEventType', 'ex:PromotionConceptScheme',
   'Trade Event Type', ARRAY['Event Type'],
   'Holiday, seasonal, special event, retailer anniversary.', 'ex:Promotion'),


  ('ex:RegularPriceBand', 'ex:PromotionConceptScheme',
   'Regular Price Band', ARRAY['Everyday Price Band'],
   'Value, mainstream, premium bands for regular price.', 'ex:Promotion'),


  ('ex:PromoPriceBand', 'ex:PromotionConceptScheme',
   'Promo Price Band', ARRAY['Deal Price Band'],
   'Deep deal, moderate deal, light deal.', 'ex:Promotion'),


  ('ex:PriceCompetitivenessBand', 'ex:PromotionConceptScheme',
   'Price Competitiveness Band', ARRAY['Price Position vs Market'],
   'Cheapest, parity, premium vs benchmark basket.', 'ex:Promotion')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:KPI', 'ex:MeasurementConceptScheme',
   'KPI', ARRAY['Key Performance Indicator'],
   'Metric or KPI used in campaign and sales measurement.', NULL),


  ('ex:KPIFamily', 'ex:MeasurementConceptScheme',
   'KPI Family', ARRAY['KPI Category'],
   'Awareness, engagement, traffic, conversion, loyalty, financial.', 'ex:KPI'),


  ('ex:KPIType', 'ex:MeasurementConceptScheme',
   'KPI Type', ARRAY['Metric Type'],
   'Reach, impressions, clicks, CTR, viewability, visits, orders, units, sales.', 'ex:KPI'),


  ('ex:IncrementalityType', 'ex:MeasurementConceptScheme',
   'Incrementality Type', ARRAY['Incremental vs Total'],
   'Incremental vs total measures.', 'ex:KPI'),


  ('ex:ShopperStatusKPI', 'ex:MeasurementConceptScheme',
   'New-to-brand vs Existing KPI', ARRAY['Shopper Status KPI'],
   'New-to-brand vs existing shopper KPI classification.', 'ex:KPI'),


  ('ex:ReturnMetricType', 'ex:MeasurementConceptScheme',
   'Return / Efficiency Metric Type', ARRAY['Return Metric'],
   'ROAS, ROI, cost per outcome metrics.', 'ex:KPI'),


  ('ex:SalesMeasureType', 'ex:MeasurementConceptScheme',
   'Sales Measure Type', ARRAY['Sales Type'],
   'Net vs gross, sell-in vs sell-out, scan vs shipment.', 'ex:KPI'),


  ('ex:SalesAttributionChannel', 'ex:MeasurementConceptScheme',
   'Sales Attribution Channel', ARRAY['Attribution Channel'],
   'In-store uplift, online uplift, omnichannel uplift.', 'ex:KPI'),


  ('ex:MarginMeasureType', 'ex:MeasurementConceptScheme',
   'Margin Measure Type', ARRAY['Margin Type'],
   'Gross margin, contribution margin.', 'ex:KPI'),


  ('ex:BasketMetricType', 'ex:MeasurementConceptScheme',
   'Basket Metric Type', ARRAY['Basket KPI'],
   'Basket size, basket value, category share of basket.', 'ex:KPI'),


  ('ex:AttributionApproachFamily', 'ex:MeasurementConceptScheme',
   'Attribution Approach Family', ARRAY['Attribution Method'],
   'Last touch, multi-touch, experimental, modeled.', 'ex:KPI'),


  ('ex:LookbackWindowBand', 'ex:MeasurementConceptScheme',
   'Lookback Window Band', ARRAY['Attribution Window Band'],
   'Short, standard, long lookback windows.', 'ex:KPI'),


  ('ex:TouchpointEligibility', 'ex:MeasurementConceptScheme',
   'Touchpoint Eligibility', ARRAY['Eligible Touchpoint Type'],
   'View, click, visit eligibility in models.', 'ex:KPI'),


  ('ex:MeasurementQualityBand', 'ex:MeasurementConceptScheme',
   'Measurement Quality Band', ARRAY['Confidence Band'],
   'Confidence or data quality bands for measurements.', 'ex:KPI')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:BusinessUnit', 'ex:OrgConceptScheme',
   'Business Unit', ARRAY['BU','Division'],
   'Internal business unit or division.', NULL),


  ('ex:MarketRole', 'ex:OrgConceptScheme',
   'Market Role', ARRAY['Global vs Local Role'],
   'Global, regional, or local market role.', 'ex:BusinessUnit'),


  ('ex:CategoryTeam', 'ex:OrgConceptScheme',
   'Category Team', ARRAY['Category Org'],
   'Team responsible for category management.', 'ex:BusinessUnit'),


  ('ex:BrandTeam', 'ex:OrgConceptScheme',
   'Brand Team', ARRAY['Brand Org'],
   'Team responsible for brand marketing.', 'ex:BusinessUnit'),


  ('ex:SalesTeam', 'ex:OrgConceptScheme',
   'Sales / Account Team', ARRAY['Account Team'],
   'Sales or account teams by retailer.', 'ex:BusinessUnit'),


  ('ex:InitiativeOwnerType', 'ex:OrgConceptScheme',
   'Initiative Owner Type', ARRAY['Ownership Type'],
   'Brand marketing, trade marketing, shopper marketing ownership.', 'ex:BusinessUnit'),


  ('ex:StrategicPillar', 'ex:OrgConceptScheme',
   'Strategic Pillar', ARRAY['Strategy Pillar'],
   'Strategic pillars such as penetration, frequency, basket, premiumization.', NULL),


  ('ex:GlobalInitiativeFramework', 'ex:OrgConceptScheme',
   'Global Initiative Framework', ARRAY['Global Program Framework'],
   'Named global initiative frameworks (e.g., Win in Omnichannel).', NULL),


  ('ex:RetailerJBPInitiative', 'ex:OrgConceptScheme',
   'Retailer Joint Business Plan Initiative', ARRAY['JBP Initiative'],
   'Joint business plan initiatives defined with retailers.', NULL)
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:CreativeObjective', 'ex:CreativeConceptScheme',
   'Creative Objective', ARRAY['Ad Objective'],
   'Objective for an individual creative (awareness, conversion, education, reassurance).', NULL),


  ('ex:MessageType', 'ex:CreativeConceptScheme',
   'Message Type', ARRAY['Message Theme'],
   'Value, quality, sustainability, convenience, lifestyle messages.', NULL),


  ('ex:BenefitFocus', 'ex:CreativeConceptScheme',
   'Benefit Focus', ARRAY['Benefit Type'],
   'Functional, emotional, social benefit focus.', NULL),


  ('ex:VisualTheme', 'ex:CreativeConceptScheme',
   'Visual Theme', ARRAY['Imagery Theme'],
   'Family moments, active lifestyle, indulgence, etc.', NULL),


  ('ex:ComplianceStatus', 'ex:CreativeConceptScheme',
   'Regulatory Compliance Status', ARRAY['Compliance Status'],
   'Regulatory-compliant vs non-compliant creative variants.', NULL),


  ('ex:ContentCategoryContext', 'ex:CreativeConceptScheme',
   'Content Category Context', ARRAY['Category Context'],
   'Context such as paired categories or cross-sell combinations.', NULL),


  ('ex:OccasionFraming', 'ex:CreativeConceptScheme',
   'Occasion Framing', ARRAY['Occasion Positioning'],
   'Everyday, special occasion, seasonal framing of the message.', 'ex:Occasion')
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:CalendarType', 'ex:TimeConceptScheme',
   'Calendar Type', ARRAY['Calendar Basis'],
   'Fiscal vs calendar vs retailer-specific calendars.', NULL),


  ('ex:FiscalCalendar', 'ex:TimeConceptScheme',
   'Fiscal Calendar', ARRAY[]::text[],
   'Company fiscal calendar hierarchy.', 'ex:CalendarType'),


  ('ex:RetailerCalendar', 'ex:TimeConceptScheme',
   'Retailer Calendar', ARRAY[]::text[],
   'Retailer-specific reporting calendar.', 'ex:CalendarType'),


  ('ex:Year', 'ex:TimeConceptScheme',
   'Year', ARRAY[]::text[],
   'Calendar or fiscal year.', NULL),


  ('ex:Quarter', 'ex:TimeConceptScheme',
   'Quarter', ARRAY['Qtr'],
   'Calendar or fiscal quarter.', 'ex:Year'),


  ('ex:Period', 'ex:TimeConceptScheme',
   'Period / Month', ARRAY['Month','Fiscal Period'],
   'Calendar month or fiscal period.', 'ex:Year'),


  ('ex:Week', 'ex:TimeConceptScheme',
   'Week', ARRAY['ISO Week','Retail Week'],
   'Week numbers (ISO or retailer-specific).', 'ex:Period'),


  ('ex:Season', 'ex:TimeConceptScheme',
   'Season', ARRAY['Seasonality'],
   'Winter, spring, summer, autumn seasons.', NULL),


  ('ex:ShoppingEvent', 'ex:TimeConceptScheme',
   'Shopping Event', ARRAY['Commercial Event'],
   'Events like Black Friday, Cyber Monday, Singles’ Day, Prime Day.', NULL),


  ('ex:CulturalHolidayEvent', 'ex:TimeConceptScheme',
   'Cultural / Holiday Event', ARRAY['Holiday Event'],
   'Easter, Christmas, Ramadan, Lunar New Year, Diwali, etc.', NULL),


  ('ex:LifeEvent', 'ex:TimeConceptScheme',
   'School / Life Event', ARRAY['Life Event'],
   'Back-to-school, graduation, weddings, and similar life events.', NULL)
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_concepts (concept_uri, scheme_uri, pref_label, alt_labels, definition, broader_uri)
VALUES
  ('ex:DataSourceType', 'ex:DataConceptScheme',
   'Data Source Type', ARRAY['Source Type'],
   'First-party, retailer data, third-party data, panel, modeled.', NULL),


  ('ex:FeedType', 'ex:DataConceptScheme',
   'Feed Type', ARRAY['Data Feed Type'],
   'Media log, POS, CRM, survey, modeling output feeds.', NULL),


  ('ex:DataSensitivityClass', 'ex:DataConceptScheme',
   'Data Sensitivity Class', ARRAY['Sensitivity Class'],
   'Internal only, retailer shareable, partner shareable.', NULL),


  ('ex:NormalizationStatus', 'ex:DataConceptScheme',
   'Normalization Status', ARRAY['Data Normalization Status'],
   'Raw, partially normalized, normalized, gold-standard.', NULL),


  ('ex:PrivacyConsentStatus', 'ex:DataConceptScheme',
   'Privacy / Consent Status', ARRAY['Consent Status'],
   'Consented, pseudonymized, aggregated, etc.', NULL)
ON CONFLICT (concept_uri) DO UPDATE SET
  scheme_uri = EXCLUDED.scheme_uri,
  pref_label = EXCLUDED.pref_label,
  alt_labels = EXCLUDED.alt_labels,
  definition = EXCLUDED.definition,
  broader_uri = EXCLUDED.broader_uri,
  updated_at = NOW();

INSERT INTO ontology_mappings (concept_uri, source_field, source_value, target_value, mapping_type, confidence)
VALUES
  ('ex:ChannelType', 'channel', 'grocery', 'grocery', 'enum', 1.0),
  ('ex:ChannelType', 'channel', 'groc', 'grocery', 'enum', 0.95),
  ('ex:ChannelType', 'channel', 'mass', 'mass', 'enum', 1.0),
  ('ex:SalesChannel', 'sales_channel', 'online', 'ecommerce', 'enum', 1.0),
  ('ex:SalesChannel', 'sales_channel', 'ecom', 'ecommerce', 'enum', 1.0),
  ('ex:SalesChannel', 'sales_channel', 'brick_and_mortar', 'brick_and_mortar', 'enum', 1.0)
ON CONFLICT (source_field, source_value, concept_uri) DO UPDATE SET
  target_value = EXCLUDED.target_value,
  mapping_type = EXCLUDED.mapping_type,
  confidence = EXCLUDED.confidence;

INSERT INTO ontology_mappings (concept_uri, source_field, source_value, target_value, mapping_type, confidence)
VALUES
  ('ex:RetailMediaPlatform', 'platform', 'walmart_connect', 'rmn_walmart', 'enum', 1.0),
  ('ex:RetailMediaPlatform', 'platform', 'wmt_connect', 'rmn_walmart', 'enum', 0.9),
  ('ex:RetailMediaPlatform', 'platform', 'amazon_ads', 'rmn_amazon', 'enum', 1.0),
  ('ex:RetailMediaPlatform', 'platform', 'ams', 'rmn_amazon', 'enum', 0.9),
  ('ex:RetailMediaPlatform', 'platform', 'roundel', 'rmn_target', 'enum', 1.0),
  ('ex:RetailMediaPlatform', 'platform', 'instacart_ads', 'rmn_instacart', 'enum', 1.0)
ON CONFLICT (source_field, source_value, concept_uri) DO UPDATE SET
  target_value = EXCLUDED.target_value,
  mapping_type = EXCLUDED.mapping_type,
  confidence = EXCLUDED.confidence;

INSERT INTO ontology_mappings (concept_uri, source_field, source_value, target_value, mapping_type, confidence)
VALUES
  ('ex:FunnelStage', 'objective_type', 'upper_funnel', 'AWARENESS', 'enum', 0.95),
  ('ex:FunnelStage', 'objective_type', 'mid_funnel', 'CONSIDERATION', 'enum', 0.95),
  ('ex:FunnelStage', 'objective_type', 'lower_funnel', 'CONVERSION', 'enum', 0.95),
  ('ex:FunnelStage', 'objective_type', 'retention', 'LOYALTY', 'enum', 0.95)
ON CONFLICT (source_field, source_value, concept_uri) DO UPDATE SET
  target_value = EXCLUDED.target_value,
  mapping_type = EXCLUDED.mapping_type,
  confidence = EXCLUDED.confidence;

INSERT INTO ontology_mappings (concept_uri, source_field, source_value, target_value, mapping_type, confidence)
VALUES
  ('ex:CreativeType', 'creative_type', 'static', 'STATIC_IMAGE', 'enum', 1.0),
  ('ex:CreativeType', 'creative_type', 'banner', 'STATIC_IMAGE', 'enum', 0.9),
  ('ex:CreativeType', 'creative_type', 'carousel', 'CAROUSEL', 'enum', 1.0),
  ('ex:CreativeType', 'creative_type', 'video', 'VIDEO', 'enum', 1.0),
  ('ex:CreativeType', 'creative_type', 'shoppable_video', 'SHOPPABLE_VIDEO', 'enum', 1.0)
ON CONFLICT (source_field, source_value, concept_uri) DO UPDATE SET
  target_value = EXCLUDED.target_value,
  mapping_type = EXCLUDED.mapping_type,
  confidence = EXCLUDED.confidence;

INSERT INTO ontology_shapes (shape_uri, target_class, shape_definition)
VALUES (
  'ex:RetailMediaImpressionShape',
  'ex:RetailMediaImpression',
  '{
    "type": "NodeShape",
    "targetClass": "ex:RetailMediaImpression",
    "property": [
      {
        "path": "schema:sku",
        "datatype": "xsd:string",
        "minCount": 1
      },
      {
        "path": "ex:retailMediaPlatform",
        "in": ["rmn_walmart", "rmn_amazon", "rmn_target", "rmn_instacart"],
        "minCount": 1
      },
      {
        "path": "ex:funnelStage",
        "in": ["AWARENESS", "CONSIDERATION", "CONVERSION", "LOYALTY"],
        "minCount": 1
      },
      {
        "path": "schema:country",
        "datatype": "xsd:string",
        "minCount": 1
      },
      {
        "path": "schema:timestamp",
        "datatype": "xsd:dateTime",
        "minCount": 1
      }
    ]
  }'::jsonb
)
ON CONFLICT (shape_uri) DO UPDATE SET
  target_class = EXCLUDED.target_class,
  shape_definition = EXCLUDED.shape_definition;

-- Commit transaction
COMMIT;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Count concepts by scheme
SELECT scheme_uri, COUNT(*) as concept_count
FROM ontology_concepts
GROUP BY scheme_uri
ORDER BY concept_count DESC;

-- Count mappings
SELECT mapping_type, COUNT(*) as mapping_count
FROM ontology_mappings
GROUP BY mapping_type;

-- Count shapes
SELECT COUNT(*) as shape_count
FROM ontology_shapes;