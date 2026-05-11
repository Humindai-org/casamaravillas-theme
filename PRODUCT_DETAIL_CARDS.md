# Product Detail Cards Section

## Overview
The `product-detail-cards` section displays key product information in a visually appealing card format with centered SVG icons. Designed for premium products (like cured meats) to showcase attributes like breed, feeding type, origin, and curing time.

## Features

### 1. **Editable Cards**
- Add, remove, or reorder cards directly from the Shopify theme editor
- Each card displays a label and value
- Fully customizable card configuration

### 2. **Data Sources**
Cards can pull data from:
- **Product Metafields**: Automatically populate from product metadata
- **Static Values**: Manual fallback or standalone content

Available metafield fields:
- `raza` (Breed): e.g., "100% Ibérica"
- `alimentacion` (Feeding): e.g., "Bellota", "Pasto", "Cereales"
- `origen` (Origin): e.g., "Jabugo, Huelva"
- `curacion` (Curing): e.g., "36–48 meses"

### 3. **Dynamic Icons**
The feeding type (`alimentacion`) field supports dynamic icon switching:
- **Bellota** (Acorn): Shows bellota icon
- **Pasto** / **Pastura** / **Grass**: Shows grass/pasture icon
- **Cereales** / **Cereal**: Shows cereals icon

Other icons are static (don't change based on product data).

## Setup Instructions

### Step 1: Add Product Metafields
In the Shopify Admin, navigate to **Settings > Metafields** and add metafield definitions if not already present:

| Key | Type | Description |
|-----|------|-------------|
| `huminda.raza` | Text | Breed information |
| `huminda.alimentacion` | Text | Feeding type |
| `huminda.origen` | Text | Origin location |
| `huminda.curacion` | Text | Curing duration |

### Step 2: Populate Product Data
For each product:
1. Go to the product details page in Shopify Admin
2. Scroll to the **Metafields** section
3. Fill in the values for raza, alimentacion, origen, and curacion

Example values:
- Raza: `100% Ibérica`
- Alimentación: `Bellota`
- Origen: `Jabugo, Huelva`
- Curación: `36–48 meses`

### Step 3: Add Section to Product Page
1. Go to your product page in the Shopify theme editor
2. Add the "Product Detail Cards" section
3. Configure the preset cards or customize as needed

## Editor Configuration

### Card Settings
For each card block, you can configure:

- **Enable this card**: Toggle to show/hide the card
- **Card Label**: Display label (e.g., "Raza", "Alimentación")
- **Data Source**: Choose where the value comes from:
  - Raza (Breed) - pulls from metafield
  - Alimentación (Feeding) - pulls from metafield
  - Origen (Origin) - pulls from metafield
  - Curación (Curing) - pulls from metafield
  - Static Value - use a fixed text value
- **Static Value**: Text to display if data source is "Static Value" or as fallback
- **Icon Type**: 
  - Static: Always uses the selected icon
  - Dynamic: Icon changes based on product's feeding type (for Alimentación field only)
- **Select Icon**: Choose from available icons

## Available Icons

- raza (Breed)
- bellota (Acorn)
- pasto (Grass/Pasture)
- cereales (Cereals)
- origen (Origin)
- consumo (Consumption)
- peso (Weight)
- conservacion (Storage)
- info (Information)
- envio (Shipping)
- garantia (Warranty)
- cata (Tasting)
- refrigerado (Refrigerated)

## Responsive Design

- **Desktop**: 4-column grid layout
- **Tablet**: 2-3 columns (auto-fit)
- **Mobile**: 2-column grid layout

The section automatically adapts to screen size for optimal viewing.

## Example Setup

### Default Preset
The section includes a pre-configured preset with four cards:
1. **Raza** - Static icon, pulls from metafield
2. **Alimentación** - Dynamic icon (changes based on feeding type), pulls from metafield
3. **Origen** - Static icon, pulls from metafield
4. **Curación** - Static icon, pulls from metafield

### Custom Configuration
You can modify or add cards to show:
- Additional product specifications
- Marketing information
- Brand highlights
- Certifications

## Technical Details

- **Namespace**: `huminda` (for all product metafields)
- **SVG Rendering**: Uses the existing `svg-icon` snippet for consistent icon handling
- **Fallback**: If a metafield is empty, displays the static value if provided
- **Mobile Optimized**: Responsive CSS with smaller icons and text on mobile devices

## CSS Classes

The section uses these CSS classes for styling:
- `.cm-product-cards`: Main container grid
- `.cm-product-card`: Individual card wrapper
- `.cm-product-card__icon`: Icon container
- `.cm-product-card__label`: Label text
- `.cm-product-card__value`: Value text

You can override these styles in your theme's main stylesheet if needed.
