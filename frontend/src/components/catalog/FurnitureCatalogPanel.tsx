/**
 * Authoritative Furniture Catalog Panel (Phase 7 Task 7.1).
 * Displays verified catalog items from PostgreSQL backend, accurate 2D metric footprint previews,
 * composite bundle definitions, and local RFA discovery audit records.
 *
 * CRITICAL: Zero hardcoded production furniture catalogs. Consumes backend API.
 */

import React, { useState, useEffect } from "react";
import {
  fetchCatalogFurniture,
  fetchCatalogBundles,
  fetchUnregisteredAssets,
  CatalogFurnitureItem,
  CatalogBundle,
  UnregisteredAsset,
} from "../../api/catalog";
import { FurnitureFootprintPreview } from "./FurnitureFootprintPreview";
import {
  Boxes,
  Package,
  Layers,
  FileQuestion,
  Search,
  PlusCircle,
  CheckCircle2,
  AlertTriangle,
  X,
  ExternalLink,
  Info,
} from "lucide-react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onAddToCanvas?: (item: CatalogFurnitureItem) => void;
}

export const FurnitureCatalogPanel: React.FC<Props> = ({
  isOpen,
  onClose,
  onAddToCanvas,
}) => {
  const [activeTab, setActiveTab] = useState<"items" | "bundles" | "unregistered">("items");
  const [items, setItems] = useState<CatalogFurnitureItem[]>([]);
  const [bundles, setBundles] = useState<CatalogBundle[]>([]);
  const [unregistered, setUnregistered] = useState<UnregisteredAsset[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setIsLoading(true);
    setError(null);

    Promise.all([
      fetchCatalogFurniture().catch(() => []),
      fetchCatalogBundles().catch(() => []),
      fetchUnregisteredAssets().catch(() => ({ unregistered_assets: [] })),
    ])
      .then(([fetchedItems, fetchedBundles, unregData]) => {
        setItems(fetchedItems);
        setBundles(fetchedBundles);
        setUnregistered(unregData.unregistered_assets || []);
      })
      .catch((err) => {
        setError(err.message || "Failed to load furniture catalog");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isOpen]);

  if (!isOpen) return null;

  const categories = ["ALL", "DESK", "CHAIR", "CONFERENCE_TABLE", "STORAGE", "CABIN", "DOOR"];

  const filteredItems = items.filter((item) => {
    const matchesCategory = selectedCategory === "ALL" || item.category === selectedCategory;
    const matchesSearch =
      !searchQuery.trim() ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.family_name && item.family_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.subtype && item.subtype.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <aside
      style={{
        position: "absolute",
        top: 0,
        right: 0,
        bottom: 0,
        width: "440px",
        backgroundColor: "#0F172A",
        borderLeft: "1px solid #1E293B",
        boxShadow: "-8px 0 24px rgba(0, 0, 0, 0.4)",
        display: "flex",
        flexDirection: "column",
        zIndex: 50,
        color: "#F8FAFC",
      }}
    >
      {/* 1. Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 20px",
          borderBottom: "1px solid #1E293B",
          backgroundColor: "#0B132B",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Boxes size={20} color="#38BDF8" />
          <div>
            <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, color: "#F8FAFC" }}>
              Authoritative Furniture Catalog
            </h2>
            <span style={{ fontSize: "0.72rem", color: "#94A3B8" }}>
              Revit RFA Physical Specifications (Phase 7 Task 7.1)
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#94A3B8",
            cursor: "pointer",
            padding: "4px",
            borderRadius: "4px",
            display: "flex",
            alignItems: "center",
          }}
        >
          <X size={18} />
        </button>
      </div>

      {/* 2. Top Navigation Tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #1E293B",
          backgroundColor: "#0B132B",
          padding: "0 12px",
          gap: "4px",
        }}
      >
        <button
          onClick={() => setActiveTab("items")}
          style={{
            flex: 1,
            padding: "10px 8px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "items" ? "2px solid #38BDF8" : "2px solid transparent",
            color: activeTab === "items" ? "#38BDF8" : "#94A3B8",
            fontWeight: 600,
            fontSize: "0.8rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
          }}
        >
          <Package size={14} />
          <span>Items ({items.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("bundles")}
          style={{
            flex: 1,
            padding: "10px 8px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "bundles" ? "2px solid #38BDF8" : "2px solid transparent",
            color: activeTab === "bundles" ? "#38BDF8" : "#94A3B8",
            fontWeight: 600,
            fontSize: "0.8rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
          }}
        >
          <Layers size={14} />
          <span>Bundles ({bundles.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("unregistered")}
          style={{
            flex: 1,
            padding: "10px 8px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "unregistered" ? "2px solid #38BDF8" : "2px solid transparent",
            color: activeTab === "unregistered" ? "#38BDF8" : "#94A3B8",
            fontWeight: 600,
            fontSize: "0.8rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
          }}
        >
          <FileQuestion size={14} />
          <span>RFA Audit ({unregistered.length})</span>
        </button>
      </div>

      {/* 3. Main Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "14px" }}>
        {error && (
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(239, 68, 68, 0.15)",
              border: "1px solid #EF4444",
              borderRadius: "6px",
              color: "#FCA5A5",
              fontSize: "0.8rem",
            }}
          >
            {error}
          </div>
        )}

        {isLoading ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#94A3B8", fontSize: "0.85rem" }}>
            Loading verified catalog specifications...
          </div>
        ) : activeTab === "items" ? (
          <>
            {/* Search Input */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                backgroundColor: "#1E293B",
                borderRadius: "6px",
                padding: "8px 12px",
                gap: "8px",
                border: "1px solid #334155",
              }}
            >
              <Search size={14} color="#94A3B8" />
              <input
                type="text"
                placeholder="Search catalog by name, family, or type..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#F8FAFC",
                  fontSize: "0.825rem",
                  width: "100%",
                  outline: "none",
                }}
              />
            </div>

            {/* Category Filter Pills */}
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "4px",
                    border: "none",
                    backgroundColor: selectedCategory === cat ? "#0284C7" : "#1E293B",
                    color: selectedCategory === cat ? "#FFFFFF" : "#94A3B8",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Catalog Items List */}
            {filteredItems.length === 0 ? (
              <div
                style={{
                  padding: "30px 16px",
                  textAlign: "center",
                  backgroundColor: "#1E293B",
                  borderRadius: "8px",
                  color: "#94A3B8",
                  fontSize: "0.825rem",
                }}
              >
                No verified catalog items found for the selected filter.
              </div>
            ) : (
              filteredItems.map((item) => (
                <div
                  key={item.catalog_item_id}
                  style={{
                    backgroundColor: "#1E293B",
                    borderRadius: "8px",
                    border: "1px solid #334155",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  {/* Card Title & Badges */}
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
                    <div>
                      <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#F8FAFC" }}>
                        {item.name}
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "#38BDF8", marginTop: "2px" }}>
                        ID: {item.catalog_item_id}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "4px", flexShrink: 0 }}>
                      <span
                        style={{
                          fontSize: "0.68rem",
                          fontWeight: 700,
                          backgroundColor: "#0369A1",
                          color: "#E0F2FE",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          textTransform: "uppercase",
                        }}
                      >
                        {item.category}
                      </span>
                      {item.is_verified && (
                        <span
                          style={{
                            fontSize: "0.68rem",
                            fontWeight: 700,
                            backgroundColor: "rgba(34, 197, 94, 0.15)",
                            color: "#4ADE80",
                            border: "1px solid #22C55E",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            display: "flex",
                            alignItems: "center",
                            gap: "3px",
                          }}
                        >
                          <CheckCircle2 size={10} />
                          Verified
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Revit Asset Reference Details */}
                  <div
                    style={{
                      backgroundColor: "#0F172A",
                      borderRadius: "6px",
                      padding: "8px 10px",
                      fontSize: "0.72rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <div>
                      <span style={{ color: "#94A3B8" }}>Revit Family: </span>
                      <span style={{ color: "#F8FAFC", fontWeight: 600 }}>{item.family_name || "N/A"}</span>
                    </div>
                    <div>
                      <span style={{ color: "#94A3B8" }}>Type Name: </span>
                      <span style={{ color: "#F8FAFC", fontWeight: 600 }}>{item.family_type_name || "N/A"}</span>
                    </div>
                    <div>
                      <span style={{ color: "#94A3B8" }}>Asset Ref: </span>
                      <span style={{ color: "#38BDF8", wordBreak: "break-all" }}>{item.source_reference || "N/A"}</span>
                    </div>
                  </div>

                  {/* 2D Metric Footprint Preview */}
                  <FurnitureFootprintPreview item={item} size={150} />

                  {/* Physical Dimensions Summary */}
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3, 1fr)",
                      gap: "6px",
                      backgroundColor: "#0F172A",
                      borderRadius: "6px",
                      padding: "8px",
                      textAlign: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "0.65rem", color: "#94A3B8" }}>WIDTH</div>
                      <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#38BDF8" }}>
                        {item.width_m.toFixed(2)} m
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.65rem", color: "#94A3B8" }}>DEPTH</div>
                      <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#38BDF8" }}>
                        {item.depth_m.toFixed(2)} m
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.65rem", color: "#94A3B8" }}>HEIGHT</div>
                      <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#38BDF8" }}>
                        {item.height_m ? `${item.height_m.toFixed(2)} m` : "—"}
                      </div>
                    </div>
                  </div>

                  {/* Add to Canvas Development Action */}
                  {onAddToCanvas && (
                    <button
                      onClick={() => onAddToCanvas(item)}
                      style={{
                        backgroundColor: "#0284C7",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: "6px",
                        padding: "8px 12px",
                        fontSize: "0.78rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        transition: "background-color 0.15s ease",
                      }}
                      onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "#0369A1")}
                      onMouseOut={(e) => (e.currentTarget.style.backgroundColor = "#0284C7")}
                    >
                      <PlusCircle size={14} />
                      <span>Add to 2D Canvas</span>
                    </button>
                  )}
                </div>
              ))
            )}
          </>
        ) : activeTab === "bundles" ? (
          /* Bundles Tab */
          <>
            <div style={{ fontSize: "0.78rem", color: "#94A3B8", lineHeight: 1.4 }}>
              Furniture bundles define composite architectural assemblies (e.g. executive desk suites with guest seating) referencing verified catalog item IDs.
            </div>

            {bundles.length === 0 ? (
              <div
                style={{
                  padding: "30px 16px",
                  textAlign: "center",
                  backgroundColor: "#1E293B",
                  borderRadius: "8px",
                  color: "#94A3B8",
                  fontSize: "0.825rem",
                }}
              >
                No composite bundles registered.
              </div>
            ) : (
              bundles.map((bundle) => (
                <div
                  key={bundle.bundle_id}
                  style={{
                    backgroundColor: "#1E293B",
                    borderRadius: "8px",
                    border: "1px solid #334155",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#F8FAFC" }}>
                        {bundle.name}
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "#38BDF8", marginTop: "2px" }}>
                        ID: {bundle.bundle_id}
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: "0.68rem",
                        fontWeight: 700,
                        backgroundColor: "#6D28D9",
                        color: "#EDE9FE",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        textTransform: "uppercase",
                      }}
                    >
                      BUNDLE
                    </span>
                  </div>

                  {bundle.description && (
                    <div style={{ fontSize: "0.75rem", color: "#94A3B8" }}>
                      {bundle.description}
                    </div>
                  )}

                  <div
                    style={{
                      backgroundColor: "#0F172A",
                      borderRadius: "6px",
                      padding: "10px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#CBD5E1" }}>
                      COMPONENTS ({bundle.components.length})
                    </div>
                    {bundle.components.map((comp) => (
                      <div
                        key={comp.component_id}
                        style={{
                          fontSize: "0.72rem",
                          display: "flex",
                          justifyContent: "space-between",
                          color: "#94A3B8",
                          borderBottom: "1px solid #1E293B",
                          paddingBottom: "4px",
                        }}
                      >
                        <span style={{ color: "#F8FAFC", fontWeight: 500 }}>
                          {comp.catalog_item_id} (×{comp.quantity})
                        </span>
                        <span>
                          Rel: ({comp.relative_x_m.toFixed(2)}m, {comp.relative_y_m.toFixed(2)}m)
                        </span>
                      </div>
                    ))}
                  </div>

                  <div style={{ fontSize: "0.72rem", color: "#64748B" }}>
                    Default Pattern: <span style={{ color: "#38BDF8", fontWeight: 600 }}>{bundle.default_arrangement}</span>
                  </div>
                </div>
              ))
            )}
          </>
        ) : (
          /* Unregistered Assets Audit Tab */
          <>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 12px",
                backgroundColor: "rgba(245, 158, 11, 0.1)",
                border: "1px solid #F59E0B",
                borderRadius: "6px",
                fontSize: "0.75rem",
                color: "#FCD34D",
              }}
            >
              <Info size={16} flexShrink={0} />
              <span>
                These real Revit RFA files exist in <code>assets/catalog/revit/</code>, but have not yet been registered because their physical dimensions and Revit type are not yet defined in <code>catalog_manifest.json</code>. Values are never fabricated.
              </span>
            </div>

            {unregistered.length === 0 ? (
              <div
                style={{
                  padding: "30px 16px",
                  textAlign: "center",
                  backgroundColor: "#1E293B",
                  borderRadius: "8px",
                  color: "#94A3B8",
                  fontSize: "0.825rem",
                }}
              >
                Zero unverified RFA assets. All local assets are verified!
              </div>
            ) : (
              unregistered.map((asset, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: "#1E293B",
                    borderRadius: "8px",
                    border: "1px solid #334155",
                    padding: "12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ fontSize: "0.825rem", fontWeight: 700, color: "#F8FAFC", wordBreak: "break-all" }}>
                      {asset.file_name}
                    </div>
                    <span
                      style={{
                        fontSize: "0.65rem",
                        fontWeight: 700,
                        backgroundColor: "rgba(245, 158, 11, 0.2)",
                        color: "#FBBF24",
                        border: "1px solid #F59E0B",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        flexShrink: 0,
                      }}
                    >
                      PENDING SPEC
                    </span>
                  </div>

                  <div style={{ fontSize: "0.7rem", color: "#38BDF8", wordBreak: "break-all" }}>
                    {asset.relative_path}
                  </div>

                  <div style={{ fontSize: "0.68rem", color: "#94A3B8" }}>
                    Size: {(asset.file_size_bytes / 1024).toFixed(1)} KB
                  </div>

                  <div
                    style={{
                      fontSize: "0.7rem",
                      color: "#94A3B8",
                      backgroundColor: "#0F172A",
                      padding: "6px 8px",
                      borderRadius: "4px",
                      marginTop: "2px",
                    }}
                  >
                    Reason: {asset.reason}
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </div>
    </aside>
  );
};
