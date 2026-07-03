/**
 * useTryOnCanvas Hook 单元测试
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTryOnCanvas } from '../useTryOnCanvas';

describe('useTryOnCanvas', () => {
  let hook: any;

  beforeEach(() => {
    hook = renderHook(() => useTryOnCanvas());
  });

  describe('初始状态', () => {
    it('应该有空的图层列表', () => {
      expect(hook.result.current.layers).toEqual([]);
    });

    it('应该没有选中图层', () => {
      expect(hook.result.current.selectedId).toBeNull();
    });

    it('应该有默认画布尺寸', () => {
      expect(hook.result.current.canvasSize).toEqual({ width: 800, height: 600 });
    });

    it('初始不能撤销', () => {
      expect(hook.result.current.canUndo).toBe(false);
    });

    it('初始不能重做', () => {
      expect(hook.result.current.canRedo).toBe(false);
    });

    it('canvasRef 初始为 null', () => {
      expect(hook.result.current.canvasRef.current).toBeNull();
    });
  });

  describe('addLayer', () => {
    it('添加图层后图层列表长度增加', () => {
      act(() => {
        hook.result.current.addLayer({
          type: 'photo',
          src: 'test.jpg',
          x: 0,
          y: 0,
          width: 100,
          height: 100,
          rotation: 0,
          opacity: 1,
          visible: true,
          name: '测试照片',
        });
      });
      expect(hook.result.current.layers).toHaveLength(1);
      expect(hook.result.current.layers[0].name).toBe('测试照片');
    });

    it('添加图层后自动选中该图层', () => {
      let addedId: string;
      act(() => {
        addedId = hook.result.current.addLayer({
          type: 'clothing',
          src: 'shirt.png',
          x: 10,
          y: 10,
          width: 50,
          height: 50,
          rotation: 0,
          opacity: 1,
          visible: true,
          name: '衬衫',
        });
      });
      expect(hook.result.current.selectedId).toBe(addedId!);
    });

    it('添加多个图层 zIndex 递增', () => {
      act(() => {
        hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
      });
      act(() => {
        hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      const zIndices = hook.result.current.layers.map((l: any) => l.zIndex);
      expect(zIndices[1]).toBeGreaterThan(zIndices[0]);
    });
  });

  describe('removeLayer', () => {
    it('删除图层后图层列表减少', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.removeLayer(layerId);
      });
      expect(hook.result.current.layers).toHaveLength(0);
    });

    it('删除选中图层后 selectedId 置空', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      expect(hook.result.current.selectedId).toBe(layerId);
      act(() => {
        hook.result.current.removeLayer(layerId);
      });
      expect(hook.result.current.selectedId).toBeNull();
    });

    it('删除非选中图层后 selectedId 不变', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
        id2 = hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      act(() => {
        hook.result.current.selectLayer(id1);
      });
      act(() => {
        hook.result.current.removeLayer(id2);
      });
      expect(hook.result.current.selectedId).toBe(id1);
    });
  });

  describe('selectLayer', () => {
    it('选中图层', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.selectLayer(layerId);
      });
      expect(hook.result.current.selectedId).toBe(layerId);
    });

    it('取消选中', () => {
      act(() => {
        hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.selectLayer(null);
      });
      expect(hook.result.current.selectedId).toBeNull();
    });
  });

  describe('moveLayer', () => {
    it('移动图层到新位置', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.moveLayer(layerId, 50, 100);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.x).toBe(50);
      expect(layer?.y).toBe(100);
    });
  });

  describe('scaleLayer', () => {
    it('缩放图层', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.scaleLayer(layerId, 200, 150);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.width).toBe(200);
      expect(layer?.height).toBe(150);
    });
  });

  describe('rotateLayer', () => {
    it('旋转图层', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.rotateLayer(layerId, 45);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.rotation).toBe(45);
    });
  });

  describe('setOpacity', () => {
    it('设置图层透明度', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.setOpacity(layerId, 0.5);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.opacity).toBe(0.5);
    });

    it('透明度不能超过1', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.setOpacity(layerId, 1.5);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.opacity).toBe(1);
    });

    it('透明度不能小于0', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.setOpacity(layerId, -0.5);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.opacity).toBe(0);
    });
  });

  describe('setLayerVisible', () => {
    it('设置图层可见性', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.setLayerVisible(layerId, false);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.visible).toBe(false);
    });
  });

  describe('reorderLayer', () => {
    it('重排序图层 zIndex', () => {
      let layerId = '';
      act(() => {
        layerId = hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.reorderLayer(layerId, 10);
      });
      const layer = hook.result.current.layers.find((l: any) => l.id === layerId);
      expect(layer?.zIndex).toBe(10);
    });
  });

  describe('setCanvasSize', () => {
    it('更新画布尺寸', () => {
      act(() => {
        hook.result.current.setCanvasSize({ width: 1920, height: 1080 });
      });
      expect(hook.result.current.canvasSize).toEqual({ width: 1920, height: 1080 });
    });
  });

  describe('undo / redo', () => {
    it('撤销操作', () => {
      act(() => {
        hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      expect(hook.result.current.layers).toHaveLength(1);
      act(() => {
        hook.result.current.undo();
      });
      expect(hook.result.current.layers).toHaveLength(0);
    });

    it('重做操作', () => {
      act(() => {
        hook.result.current.addLayer({
          type: 'photo', src: 'test.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '测试',
        });
      });
      act(() => {
        hook.result.current.undo();
      });
      expect(hook.result.current.layers).toHaveLength(0);
      act(() => {
        hook.result.current.redo();
      });
      expect(hook.result.current.layers).toHaveLength(1);
    });

    it('初始状态不能撤销', () => {
      act(() => {
        hook.result.current.undo();
      });
      expect(hook.result.current.layers).toHaveLength(0);
    });

    it('初始状态不能重做', () => {
      act(() => {
        hook.result.current.redo();
      });
      expect(hook.result.current.layers).toHaveLength(0);
    });

    it('新操作后重做历史被清除', () => {
      act(() => {
        hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
      });
      act(() => {
        hook.result.current.undo();
      });
      act(() => {
        hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      // 此时重做应该不可用（新操作覆盖了重做历史）
      expect(hook.result.current.canRedo).toBe(false);
    });
  });

  describe('exportCanvas', () => {
    it('没有 canvas 时返回 null', () => {
      const result = hook.result.current.exportCanvas();
      expect(result).toBeNull();
    });

    it('有 canvas 时返回 dataURL', () => {
      const mockCanvas = document.createElement('canvas');
      mockCanvas.toDataURL = () => 'data:image/png;base64,test';
      hook.result.current.canvasRef.current = mockCanvas;
      const result = hook.result.current.exportCanvas();
      expect(result).toBe('data:image/png;base64,test');
      hook.result.current.canvasRef.current = null;
    });
  });

  describe('多图层更新（非目标图层不受影响）', () => {
    it('移动图层时其他图层不变', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
        id2 = hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 10, y: 10, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      act(() => {
        hook.result.current.moveLayer(id1, 99, 99);
      });
      const layer2 = hook.result.current.layers.find((l: any) => l.id === id2);
      expect(layer2?.x).toBe(10);
      expect(layer2?.y).toBe(10);
    });

    it('缩放图层时其他图层不变', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
        id2 = hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      act(() => {
        hook.result.current.scaleLayer(id1, 200, 200);
      });
      const layer2 = hook.result.current.layers.find((l: any) => l.id === id2);
      expect(layer2?.width).toBe(50);
    });

    it('旋转图层时其他图层不变', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
        id2 = hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      act(() => {
        hook.result.current.rotateLayer(id1, 90);
      });
      const layer2 = hook.result.current.layers.find((l: any) => l.id === id2);
      expect(layer2?.rotation).toBe(0);
    });

    it('设置透明度时其他图层不变', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
        id2 = hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      act(() => {
        hook.result.current.setOpacity(id1, 0.3);
      });
      const layer2 = hook.result.current.layers.find((l: any) => l.id === id2);
      expect(layer2?.opacity).toBe(1);
    });

    it('设置可见性时其他图层不变', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
        id2 = hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      act(() => {
        hook.result.current.setLayerVisible(id1, false);
      });
      const layer2 = hook.result.current.layers.find((l: any) => l.id === id2);
      expect(layer2?.visible).toBe(true);
    });

    it('重排序图层时其他图层 zIndex 不变', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = hook.result.current.addLayer({
          type: 'photo', src: 'a.jpg', x: 0, y: 0, width: 100, height: 100,
          rotation: 0, opacity: 1, visible: true, name: '图层1',
        });
        id2 = hook.result.current.addLayer({
          type: 'clothing', src: 'b.png', x: 0, y: 0, width: 50, height: 50,
          rotation: 0, opacity: 1, visible: true, name: '图层2',
        });
      });
      const z2Before = hook.result.current.layers.find((l: any) => l.id === id2)?.zIndex;
      act(() => {
        hook.result.current.reorderLayer(id1, 99);
      });
      const layer2 = hook.result.current.layers.find((l: any) => l.id === id2);
      expect(layer2?.zIndex).toBe(z2Before);
    });
  });

  describe('最大历史记录', () => {
    it('超过最大历史时丢弃最早的记录', () => {
      // 添加超过 MAX_HISTORY (50) 次的操作
      for (let i = 0; i < 55; i++) {
        act(() => {
          hook.result.current.addLayer({
            type: 'photo', src: `img${i}.jpg`, x: 0, y: 0, width: 100, height: 100,
            rotation: 0, opacity: 1, visible: true, name: `图层${i}`,
          });
        });
      }
      expect(hook.result.current.layers.length).toBe(55);
      // canUndo 应该仍然为 true
      expect(hook.result.current.canUndo).toBe(true);
    });
  });
});
