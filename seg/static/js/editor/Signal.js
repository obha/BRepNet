class Signal {
  constructor() {
    this._subscribers = [];
  }

  dispatch(...args) {
    for (let subscriber of this._subscribers) {
      subscriber(...args);
    }
  }

  add(subscriber) {
    this._subscribers.push(subscriber);
  }
}

export { Signal };
