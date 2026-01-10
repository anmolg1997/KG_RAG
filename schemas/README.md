# Schema Definition Guide

This directory contains **schema definitions** that tell the KG-RAG system how to understand your documents.

## 🎯 What is a Schema?

A schema is like a **blueprint** that defines:
1. **What entities to extract** (e.g., Person, Organization, Date)
2. **What properties each entity has** (e.g., name, type, address)
3. **How entities relate to each other** (e.g., Person WORKS_FOR Organization)

## 📁 Available Schemas

| Schema | File | Description |
|--------|------|-------------|
| Contract | `contract.yaml` | Legal contracts, agreements, NDAs |
| Research Paper | `research_paper.yaml` | Academic papers, publications |
| Invoice | `invoice.yaml` | Financial invoices, receipts |

## 🔧 How to Create a New Schema

### Step 1: Copy the Template

```bash
cp contract.yaml my_domain.yaml
```

### Step 2: Define Your Entities

Think about **what things** exist in your documents:

```yaml
entities:
  - name: MyEntity
    description: "What this entity represents"
    color: "#hexcolor"  # For visualization
    
    properties:
      - name: property_name
        type: string|number|date|boolean|enum|text|list
        required: true|false
        description: "What this property represents"
```

### Step 3: Define Relationships

Think about **how entities connect**:

```yaml
relationships:
  - name: RELATIONSHIP_NAME
    source: EntityA
    target: EntityB
    description: "EntityA has this relationship to EntityB"
```

### Step 4: Set as Active Schema

In your `.env` file:
```
ACTIVE_SCHEMA=my_domain
```

## 📊 Property Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Short text | Name, title |
| `text` | Long text | Description, summary |
| `number` | Numeric value | Amount, count |
| `date` | Date value | YYYY-MM-DD |
| `boolean` | True/false | is_active |
| `enum` | Fixed choices | status: [active, inactive] |
| `list` | Array of items | tags: ["tag1", "tag2"] |

## 🎨 Entity Colors

Choose colors for graph visualization:
- Use hex codes: `"#38b2ac"`
- Recommended palette:
  - Primary entities: `#38b2ac` (teal)
  - People/Organizations: `#f59e0b` (amber)
  - Categories: `#8b5cf6` (purple)
  - Actions: `#ef4444` (red)
  - Dates: `#10b981` (green)
  - Numbers: `#3b82f6` (blue)

## 🔄 Schema Validation

The system automatically validates:
- Required properties are present
- Enum values are valid
- Relationships reference existing entities
- No circular dependencies

## 💡 Tips

1. **Start simple**: Begin with 3-5 entity types
2. **Be specific**: Clear descriptions help the LLM
3. **Use examples**: Add query_examples for common questions
4. **Iterate**: Refine based on extraction results
