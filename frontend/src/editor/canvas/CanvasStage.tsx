/**
 * Konva Canvas Stage Component.
 * Handles responsive sizing, free canvas pan, cursor-anchored zoom, and floor-plan rendering.
 */
import React, { useRef, useEffect, useState, useCallback } from "react";
import { Stage, Layer } from "react-konva";
import Konva from "konva";
import { Viewport, Point2D } from "./canvasTypes";
import { CanvasGrid } from "./CanvasGrid";
import { screenToWorld, zoomAtPoint, fitBounds } from "./viewport";
import { FloorPlanRenderModel } from "../renderer/renderTypes";
import { KonvaFloorPlanRenderer } from "../renderer/KonvaRendererAdapter";
import { SnapGuideLine } from "../snapping/snappingTypes";
import { TransformChange } from "../transforms/transformTypes";

interface CanvasStageProps {
  viewport: Viewport; onViewportChange: (v: Viewport) => void; onCursorMove?: (p: Point2D) => void;
  showGrid?: boolean; renderModel?: FloorPlanRenderModel; selectedObjectId?: string | null;
  onSelectObject?: (id: string | null) => void; onTransformChange?: (c: TransformChange) => void;
  onSnapGuidesChange?: (g: SnapGuideLine[]) => void; snapGuides?: SnapGuideLine[];
  onFitView?: (fit: () => void) => void;
}
export const CanvasStage: React.FC<CanvasStageProps> = (p) => {
  const { viewport,onViewportChange,onCursorMove,showGrid=true,renderModel,selectedObjectId=null,onSelectObject,onTransformChange,onSnapGuidesChange,snapGuides=[],onFitView }=p;
  const containerRef=useRef<HTMLDivElement>(null); const stageRef=useRef<Konva.Stage>(null);
  const hasFittedRef=useRef<string|null>(null); const [containerSize,setContainerSize]=useState({width:800,height:600});
  const [isPanning,setIsPanning]=useState(false); const panStartRef=useRef({x:0,y:0});

  useEffect(()=>{ if(!containerRef.current)return; const observer=new ResizeObserver(entries=>{const r=entries[0]?.contentRect;if(r)setContainerSize({width:Math.max(200,r.width),height:Math.max(200,r.height)});}); observer.observe(containerRef.current); return()=>observer.disconnect();},[]);
  const fitView=useCallback(()=>{if(renderModel)onViewportChange(fitBounds(renderModel.boundary,containerSize.width,containerSize.height));},[renderModel,containerSize,onViewportChange]);
  useEffect(()=>{if(!renderModel||containerSize.width<=0||containerSize.height<=0)return;if(hasFittedRef.current===renderModel.id)return;hasFittedRef.current=renderModel.id;fitView();},[renderModel,containerSize.width,containerSize.height,fitView]);
  useEffect(()=>{onFitView?.(fitView);},[onFitView,fitView]);
  useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==="Escape"){onSelectObject?.(null);onSnapGuidesChange?.([]);}};window.addEventListener("keydown",key);return()=>window.removeEventListener("keydown",key);},[onSelectObject,onSnapGuidesChange]);

  const handleWheel=useCallback((e:Konva.KonvaEventObject<WheelEvent>)=>{e.evt.preventDefault();const pt=stageRef.current?.getPointerPosition();if(pt)onViewportChange(zoomAtPoint(pt,e.evt.deltaY<0?1.1:0.9,viewport));},[viewport,onViewportChange]);
  const handleDoubleClick=useCallback(()=>{const pt=stageRef.current?.getPointerPosition();if(pt)onViewportChange(zoomAtPoint(pt,1.5,viewport));},[viewport,onViewportChange]);
  const handleMouseMove=useCallback((e:Konva.KonvaEventObject<MouseEvent>)=>{const stage=stageRef.current;if(!stage)return;const pt=stage.getPointerPosition();if(pt&&onCursorMove)onCursorMove(screenToWorld(pt,viewport));if(isPanning){const dx=e.evt.clientX-panStartRef.current.x,dy=e.evt.clientY-panStartRef.current.y;panStartRef.current={x:e.evt.clientX,y:e.evt.clientY};onViewportChange({...viewport,x:viewport.x+dx,y:viewport.y+dy});}},[isPanning,viewport,onViewportChange,onCursorMove]);
  const handleMouseDown=useCallback((e:Konva.KonvaEventObject<MouseEvent>)=>{const targetIsStage=e.target===e.target.getStage();if(!targetIsStage&&e.evt.button===0)return;if(e.evt.button===0||e.evt.button===1||e.evt.shiftKey){setIsPanning(true);panStartRef.current={x:e.evt.clientX,y:e.evt.clientY};if(e.evt.button===0)onSelectObject?.(null);return;}if(targetIsStage)onSelectObject?.(null);},[onSelectObject]);
  return <div ref={containerRef} style={{width:"100%",height:"100%",position:"relative",overflow:"hidden",backgroundColor:"#0f172a",cursor:isPanning?"grabbing":"default"}}>
    <Stage ref={stageRef} width={containerSize.width} height={containerSize.height} onWheel={handleWheel} onDblClick={handleDoubleClick} onMouseMove={handleMouseMove} onMouseDown={handleMouseDown} onMouseUp={()=>setIsPanning(false)}>
      {showGrid&&<CanvasGrid viewport={viewport} containerWidth={containerSize.width} containerHeight={containerSize.height}/>}
      <Layer>{renderModel&&<KonvaFloorPlanRenderer model={renderModel} viewport={viewport} selectedObjectId={selectedObjectId} onSelectObject={onSelectObject} onTransformChange={onTransformChange} onSnapGuidesChange={onSnapGuidesChange} snapGuides={snapGuides}/>}</Layer>
    </Stage>
  </div>;
};
