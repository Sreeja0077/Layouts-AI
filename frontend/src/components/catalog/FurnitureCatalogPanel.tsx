/**
 * Authoritative Furniture Catalog Panel (Phase 7 Task 7.1).
 * Professional BIM Asset Browser for Revit RFA specifications.
 * Consumes backend API dynamically - zero hardcoded catalogs.
 */

import React, { useState, useEffect } from "react";
import {
  fetchCatalogFurniture,
  fetchCatalogBundles,
  fetchUnregisteredAssets,
  CatalogFurnitureItem,
  CatalogBundle,
  UnregisteredAsset,
  UnregisteredAssetsResponse,
} from "../../api/catalog";
import { FurnitureFootprintPreview } from "./FurnitureFootprintPreview";
import {
  Boxes,
  Package,
  Layers,
  FileQuestion,
  Search,
  Plus,
  CheckCircle2,
  AlertCircle,
  X,
  ChevronDown,
  ChevronRight,
  FolderArchive,
  Ruler,
  Maximize2,
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
  const [auditMeta, setAuditMeta] = useState<UnregisteredAssetsResponse | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setIsLoading(true);
    setError(null);

    Promise.all([
      fetchCatalogFurniture().catch(() => []),
      fetchCatalogBundles().catch(() => []),
      fetchUnregisteredAssets().catch(() => ({
        total_rfa_files_found: 0,
        registered_items_count: 0,
        unregistered_rfa_count: 0,
        unregistered_assets: [],
      })),
    ])
      .then(([fetchedItems, fetchedBundles, unregData]) => {
        setItems(fetchedItems);
        setBundles(fetchedBundles);
        setAuditMeta(unregData);
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

  const toggleDetails = (id: string) => {
    setExpandedDetails((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const categories = ["ALL", "DESK", "CHAIR", "CONFERENCE_TABLE", "STORAGE", "CABIN", "DOOR"];

  const filteredItems = items.filter((item) => {
    const matchesCategory = selectedCategory === "ALL" || item.category === selectedCategory;
    const matchesSearch =
      !searchQuery.trim() ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.family_name && item.family_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.subtype && item.subtype.toLowerCase().includes(searchQuery.toLowerCase())) ||
      item.catalog_item_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const totalDiscovered = auditMeta?.total_rfa_files_found || (items.length + unregistered.length);
  const verifiedCount = items.length;
  const pendingCount = unregistered.length;

  return (
    <aside
      style={{
        position: "absolute",
        top: 0,
        right: 0,
        bottom: 0,
        width: "420px",
        backgroundColor: "#0B1120",
        borderLeft: "1px solid #1E293B",
        boxShadow: "-8px 0 24px rgba(0, 0, 0, 0.45)",
        display: "flex",
        flexDirection: "column",
        zIndex: 50,
        color: "#F8FAFC",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* 1. CAD Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 16px",
          borderBottom: "1px solid #1E293B",
          backgroundColor: "#0F172A",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "6px",
              backgroundColor: "rgba(14, 165, 233, 0.15)",
              border: "1px solid rgba(14, 165, 233, 0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Boxes size={16} color="#38BDF8" />
          </div>
          <div>
            <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#F8FAFC", letterSpacing: "-0.01em" }}>
              BIM Furniture Catalog
            </div>
            <div style={{ fontSize: "0.72rem", color: "#94A3B8", marginTop: "1px" }}>
              <span style={{ color: "#38BDF8", fontWeight: 600 }}>{totalDiscovered}</span> discovered ·{" "}
              <span style={{ color: "#4ADE80", fontWeight: 600 }}>{verifiedCount}</span> verified ·{" "}
              <span style={{ color: "#FBBF24", fontWeight: 600 }}>{pendingCount}</span> pending
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          title="Close Catalog Drawer"
          style={{
            background: "transparent",
            border: "1px solid transparent",
            color: "#94A3B8",
            cursor: "pointer",
            padding: "5px",
            borderRadius: "5px",
            display: "flex",
            alignItems: "center",
            transition: "all 0.15s ease",
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.color = "#F8FAFC";
            e.currentTarget.style.backgroundColor = "#1E293B";
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.color = "#94A3B8";
            e.currentTarget.style.backgroundColor = "transparent";
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* 2. Compact CAD Tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #1E293B",
          backgroundColor: "#0B1120",
          padding: "0 10px",
          gap: "2px",
        }}
      >
        <button
          onClick={() => setActiveTab("items")}
          style={{
            flex: 1,
            padding: "10px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "items" ? "2px solid #38BDF8" : "2px solid transparent",
            color: activeTab === "items" ? "#38BDF8" : "#94A3B8",
            fontWeight: 600,
            fontSize: "0.78rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "5px",
          }}
        >
          <Package size={13} />
          <span>Items ({items.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("bundles")}
          style={{
            flex: 1,
            padding: "10px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "bundles" ? "2px solid #38BDF8" : "2px solid transparent",
            color: activeTab === "bundles" ? "#38BDF8" : "#94A3B8",
            fontWeight: 600,
            fontSize: "0.78rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "5px",
          }}
        >
          <Layers size={13} />
          <span>Bundles ({bundles.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("unregistered")}
          style={{
            flex: 1,
            padding: "10px 4px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "unregistered" ? "2px solid #F59E0B" : "2px solid transparent",
            color: activeTab === "unregistered" ? "#F59E0B" : "#94A3B8",
            fontWeight: 600,
            fontSize: "0.78rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "5px",
          }}
        >
          <FileQuestion size={13} />
          <span>RFA Audit ({unregistered.length})</span>
        </button>
      </div>

      {/* 3. Main Body */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "14px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {error && (
          <div
            style={{
              padding: "10px 12px",
              backgroundColor: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "6px",
              color: "#FCA5A5",
              fontSize: "0.78rem",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <AlertCircle size={14} flexShrink={0} />
            <span>{error}</span>
          </div>
        )}

        {isLoading ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748B", fontSize: "0.82rem" }}>
            Scanning Revit assets and catalog metadata...
          </div>
        ) : activeTab === "items" ? (
          <>
            {/* Search Input */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                backgroundColor: "#0F172A",
                borderRadius: "6px",
                padding: "7px 10px",
                gap: "8px",
                border: "1px solid #1E293B",
              }}
            >
              <Search size={14} color="#64748B" />
              <input
                type="text"
                placeholder="Search catalog by name, family, type..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#F8FAFC",
                  fontSize: "0.8rem",
                  width: "100%",
                  outline: "none",
                }}
              />
            </div>

            {/* Category Filter Pills */}
            <div style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  style={{
                    padding: "3px 8px",
                    borderRadius: "4px",
                    border: "1px solid " + (selectedCategory === cat ? "#0284C7" : "#1E293B"),
                    backgroundColor: selectedCategory === cat ? "#0369A1" : "#0F172A",
                    color: selectedCategory === cat ? "#FFFFFF" : "#94A3B8",
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.1s ease",
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
                  padding: "32px 16px",
                  textAlign: "center",
                  backgroundColor: "#0F172A",
                  borderRadius: "6px",
                  border: "1px solid #1E293B",
                  color: "#64748B",
                  fontSize: "0.8rem",
                }}
              >
                No verified catalog items found matching criteria.
              </div>
            ) : (
              filteredItems.map((item) => {
                const isExpanded = !!expandedDetails[item.catalog_item_id];
                return (
                  <div
                    key={item.catalog_item_id}
                    style={{
                      backgroundColor: "#0F172A",
                      borderRadius: "6px",
                      border: "1px solid #1E293B",
                      padding: "12px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    {/* Primary Row: Name, Category, Verified Chip */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                      <div>
                        <div style={{ fontSize: "0.86rem", fontWeight: 700, color: "#F8FAFC" }}>
                          {item.name}
                        </div>
                        <div style={{ display: "flex", gap: "6px", alignItems: "center", marginTop: "3px" }}>
                          <span
                            style={{
                              fontSize: "0.64rem",
                              fontWeight: 700,
                              backgroundColor: "rgba(14, 165, 233, 0.15)",
                              color: "#38BDF8",
                              padding: "1px 5px",
                              borderRadius: "3px",
                              border: "1px solid rgba(14, 165, 233, 0.25)",
                            }}
                          >
                            {item.category}
                          </span>
                          {item.subtype && (
                            <span
                              style={{
                                fontSize: "0.64rem",
                                color: "#94A3B8",
                              }}
                            >
                              {item.subtype}
                            </span>
                          )}
                        </div>
                      </div>

                      {item.is_verified && (
                        <span
                          style={{
                            fontSize: "0.64rem",
                            fontWeight: 600,
                            backgroundColor: "rgba(34, 197, 94, 0.12)",
                            color: "#4ADE80",
                            border: "1px solid rgba(34, 197, 94, 0.25)",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            display: "flex",
                            alignItems: "center",
                            gap: "3px",
                            flexShrink: 0,
                          }}
                        >
                          <CheckCircle2 size={10} />
                          Verified RFA
                        </span>
                      )}
                    </div>

                    {/* Primary Footprint & Metric Preview */}
                    <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                      <FurnitureFootprintPreview item={item} size={110} />
                      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
                        <div
                          style={{
                            backgroundColor: "#1E293B",
                            borderRadius: "5px",
                            padding: "6px 8px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                          }}
                        >
                          <span style={{ fontSize: "0.7rem", color: "#94A3B8", display: "flex", alignItems: "center", gap: "4px" }}>
                            <Ruler size={12} color="#38BDF8" /> Dimensions:
                          </span>
                          <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#38BDF8" }}>
                            {item.width_m.toFixed(2)} × {item.depth_m.toFixed(2)} m
                          </span>
                        </div>

                        {item.height_m && (
                          <div
                            style={{
                              backgroundColor: "#1E293B",
                              borderRadius: "5px",
                              padding: "4px 8px",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                            }}
                          >
                            <span style={{ fontSize: "0.68rem", color: "#94A3B8" }}>Height:</span>
                            <span style={{ fontSize: "0.72rem", color: "#CBD5E1" }}>
                              {item.height_m.toFixed(2)} m
                            </span>
                          </div>
                        )}

                        {onAddToCanvas && (
                          <button
                            onClick={() => onAddToCanvas(item)}
                            title="Place onto 2D canvas in world coordinates"
                            style={{
                              backgroundColor: "#0284C7",
                              color: "#FFFFFF",
                              border: "none",
                              borderRadius: "5px",
                              padding: "6px 10px",
                              fontSize: "0.74rem",
                              fontWeight: 600,
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              gap: "4px",
                              marginTop: "2px",
                              transition: "background-color 0.12s ease",
                            }}
                            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "#0369A1")}
                            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = "#0284C7")}
                          >
                            <Plus size={13} />
                            <span>Add to Canvas</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Secondary Collapsible Details */}
                    <div>
                      <button
                        onClick={() => toggleDetails(item.catalog_item_id)}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#64748B",
                          fontSize: "0.7rem",
                          fontWeight: 500,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "3px",
                          padding: 0,
                        }}
                      >
                        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                        <span>{isExpanded ? "Hide BIM Details" : "Show BIM Details"}</span>
                      </button>

                      {isExpanded && (
                        <div
                          style={{
                            marginTop: "6px",
                            backgroundColor: "#080D1A",
                            borderRadius: "5px",
                            padding: "8px",
                            border: "1px solid #1E293B",
                            fontSize: "0.68rem",
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                          }}
                        >
                          <div>
                            <span style={{ color: "#64748B" }}>Family Name: </span>
                            <span style={{ color: "#F8FAFC", fontWeight: 600 }}>{item.family_name || "N/A"}</span>
                          </div>
                          <div>
                            <span style={{ color: "#64748B" }}>Type Name: </span>
                            <span style={{ color: "#F8FAFC", fontWeight: 600 }}>{item.family_type_name || "N/A"}</span>
                          </div>
                          <div>
                            <span style={{ color: "#64748B" }}>Catalog ID: </span>
                            <span style={{ color: "#38BDF8", fontFamily: "monospace" }}>{item.catalog_item_id}</span>
                          </div>
                          <div>
                            <span style={{ color: "#64748B" }}>Asset Source: </span>
                            <span style={{ color: "#94A3B8", wordBreak: "break-all" }}>{item.source_reference || "N/A"}</span>
                          </div>
                          {item.clearance && (
                            <div style={{ color: "#64748B" }}>
                              Clearance: Front {item.clearance.front_m}m · Back {item.clearance.back_m}m · Sides {item.clearance.left_m}m
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </>
        ) : activeTab === "bundles" ? (
          <>
            {bundles.length === 0 ? (
              <div
                style={{
                  padding: "32px 16px",
                  textAlign: "center",
                  backgroundColor: "#0F172A",
                  borderRadius: "6px",
                  border: "1px solid #1E293B",
                  color: "#64748B",
                  fontSize: "0.8rem",
                }}
              >
                No bundle definitions registered in the catalog.
              </div>
            ) : (
              bundles.map((bundle) => (
                <div
                  key={bundle.bundle_id}
                  style={{
                    backgroundColor: "#0F172A",
                    borderRadius: "6px",
                    border: "1px solid #1E293B",
                    padding: "12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: "0.86rem", fontWeight: 700, color: "#F8FAFC" }}>
                        {bundle.name}
                      </div>
                      <div style={{ fontSize: "0.68rem", color: "#64748B", marginTop: "2px" }}>
                        ID: {bundle.bundle_id}
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: "0.64rem",
                        fontWeight: 700,
                        backgroundColor: "rgba(168, 85, 247, 0.15)",
                        color: "#C084FC",
                        border: "1px solid rgba(168, 85, 247, 0.3)",
                        padding: "1px 5px",
                        borderRadius: "3px",
                      }}
                    >
                      {bundle.category} BUNDLE
                    </span>
                  </div>

                  {bundle.description && (
                    <div style={{ fontSize: "0.72rem", color: "#94A3B8" }}>
                      {bundle.description}
                    </div>
                  )}

                  {/* Components breakdown */}
                  <div
                    style={{
                      backgroundColor: "#080D1A",
                      borderRadius: "5px",
                      padding: "8px",
                      border: "1px solid #1E293B",
                      display: "flex",
                      flexDirection: "column",
                      gap: "5px",
                    }}
                  >
                    <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#94A3B8" }}>
                      COMPONENTS ({bundle.components.length})
                    </div>
                    {bundle.components.map((comp) => (
                      <div
                        key={comp.component_id}
                        style={{
                          fontSize: "0.7rem",
                          display: "flex",
                          justifyContent: "space-between",
                          color: "#CBD5E1",
                        }}
                      >
                        <span>
                          {comp.catalog_item_id} <span style={{ color: "#38BDF8" }}>(×{comp.quantity})</span>
                        </span>
                        <span style={{ color: "#64748B" }}>
                          Offset: ({comp.relative_x_m.toFixed(2)}m, {comp.relative_y_m.toFixed(2)}m)
                        </span>
                      </div>
                    ))}
                  </div>

                  <div style={{ fontSize: "0.68rem", color: "#64748B" }}>
                    Pattern Arrangement:{" "}
                    <span style={{ color: "#38BDF8", fontWeight: 600 }}>{bundle.default_arrangement}</span>
                  </div>
                </div>
              ))
            )}
          </>
        ) : (
          /* RFA Audit Tab */
          <>
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "8px",
                padding: "10px",
                backgroundColor: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.25)",
                borderRadius: "6px",
                fontSize: "0.72rem",
                color: "#FCD34D",
                lineHeight: "1.35",
              }}
            >
              <AlertCircle size={14} style={{ marginTop: "1px", flexShrink: 0 }} />
              <div>
                <strong>Revit RFA Audit:</strong> Real assets found in <code>assets/catalog/revit/</code> awaiting verified dimensions and family specifications. Dimensions are never fabricated.
              </div>
            </div>

            {unregistered.length === 0 ? (
              <div
                style={{
                  padding: "32px 16px",
                  textAlign: "center",
                  backgroundColor: "#0F172A",
                  borderRadius: "6px",
                  border: "1px solid #1E293B",
                  color: "#64748B",
                  fontSize: "0.8rem",
                }}
              >
                Zero pending assets. All discovered RFA files are verified!
              </div>
            ) : (
              unregistered.map((asset, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: "#0F172A",
                    borderRadius: "6px",
                    border: "1px solid #1E293B",
                    padding: "10px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "5px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "6px" }}>
                    <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#F8FAFC", wordBreak: "break-all" }}>
                      {asset.file_name}
                    </div>
                    <span
                      style={{
                        fontSize: "0.62rem",
                        fontWeight: 700,
                        backgroundColor: asset.status === "INVALID_METADATA" ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
                        color: asset.status === "INVALID_METADATA" ? "#F87171" : "#FBBF24",
                        border: "1px solid " + (asset.status === "INVALID_METADATA" ? "rgba(239, 68, 68, 0.3)" : "rgba(245, 158, 11, 0.3)"),
                        padding: "1px 5px",
                        borderRadius: "3px",
                        flexShrink: 0,
                      }}
                    >
                      {asset.status === "INVALID_METADATA" ? "INVALID SPEC" : "PENDING METADATA"}
                    </span>
                  </div>

                  <div style={{ fontSize: "0.68rem", color: "#38BDF8", wordBreak: "break-all" }}>
                    {asset.relative_path}
                  </div>

                  <div style={{ fontSize: "0.65rem", color: "#64748B" }}>
                    Size: {(asset.file_size_bytes / 1024).toFixed(1)} KB
                  </div>

                  <div
                    style={{
                      fontSize: "0.68rem",
                      color: "#94A3B8",
                      backgroundColor: "#080D1A",
                      padding: "5px 7px",
                      borderRadius: "4px",
                      border: "1px solid #1E293B",
                    }}
                  >
                    Reason: {asset.reason}
                  </div>

                  {asset.missing_fields && asset.missing_fields.length > 0 && (
                    <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "2px" }}>
                      <span style={{ fontSize: "0.62rem", color: "#64748B" }}>Missing:</span>
                      {asset.missing_fields.map((fld) => (
                        <span
                          key={fld}
                          style={{
                            fontSize: "0.6rem",
                            backgroundColor: "#1E293B",
                            color: "#CBD5E1",
                            padding: "1px 4px",
                            borderRadius: "3px",
                          }}
                        >
                          {fld}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </>
        )}
      </div>
    </aside>
  );
};
