/**
 * In-Memory Event Bus
 * Supports both topic-based (publish/subscribe) and event-based (on/emit) patterns
 */

export class InMemoryEventBus {
  constructor() {
    this.handlers = new Map();
    this.eventHandlers = new Map();
    this.__id = `eventbus_${Math.random().toString(36).substr(2, 9)}`;
  }

  publish(topic, event) {
    const set = this.handlers.get(topic);
    if (!set || set.size === 0) {
      console.log(`[EventBus:${this.__id}] 📤 Published "${topic}" but no subscribers (${set?.size || 0})`);
      return;
    }
    console.log(`[EventBus:${this.__id}] 📤 Publishing "${topic}" to ${set.size} subscriber(s)`);
    for (const h of set) {
      try { h(event); } catch (e) { console.error('Event handler error', e); }
    }
  }

  subscribe(topic, handler) {
    const set = this.handlers.get(topic) || new Set();
    set.add(handler);
    this.handlers.set(topic, set);
    console.log(`[EventBus:${this.__id}] 📥 Subscribed to "${topic}" (total: ${set.size})`);
    return {
      unsubscribe: () => {
        const s = this.handlers.get(topic);
        if (!s) return;
        s.delete(handler);
        if (s.size === 0) this.handlers.delete(topic);
      }
    };
  }

  on(event, handler) {
    const set = this.eventHandlers.get(event) || new Set();
    set.add(handler);
    this.eventHandlers.set(event, set);
    console.log(`[EventBus:${this.__id}] 📥 Listening to "${event}" (total: ${set.size})`);
  }

  emit(event, data) {
    const set = this.eventHandlers.get(event);
    if (!set || set.size === 0) {
      console.log(`[EventBus:${this.__id}] 📤 Emitted "${event}" but no listeners (${set?.size || 0})`);
      return;
    }
    console.log(`[EventBus:${this.__id}] 📤 Emitting "${event}" to ${set.size} listener(s)`);
    for (const h of set) {
      try { h(data); } catch (e) { console.error('Event handler error', e); }
    }
  }

  off(event, handler) {
    const set = this.eventHandlers.get(event);
    if (!set) return;
    if (handler) {
      set.delete(handler);
      if (set.size === 0) this.eventHandlers.delete(event);
    } else {
      this.eventHandlers.delete(event);
    }
  }
}

// Singleton instance for shared use across the application
export const eventBus = new InMemoryEventBus();

// Log event bus initialization
console.log(`🔌 [EventBus] Shared singleton initialized: ${eventBus.__id}`);

