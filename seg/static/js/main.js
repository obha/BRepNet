import { Editor } from "./editor/Editor.js";

class SegmentationEditor extends Editor {
  constructor() {
    super();

    this.ws = new WebSocket("ws://localhost:8765");
    this.ws.onopen = this.onopen.bind(this);
    this.ws.onmessage = this.onmessage.bind(this);
  }

  onopen(event) {}

  onmessage(event) {
    console.log(event);
  }

  render(renderer) {
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);

    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const backgroundColor = 0x222222; //0xa0a0a0
    this.scene.background = new THREE.Color(backgroundColor);
    this.scene.fog = new THREE.Fog(backgroundColor, 200, 600);

    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();

    // Create two lights to evenly illuminate the model and cast shadows
    const light = new THREE.HemisphereLight(0xffffff, 0x444444);
    light.position.set(0, 200, 0);
    const light2 = new THREE.DirectionalLight(0xbbbbbb);
    light2.position.set(6, 50, -12);
    light2.castShadow = true;
    light2.shadow.camera.top = 200;
    light2.shadow.camera.bottom = -200;
    light2.shadow.camera.left = -200;
    light2.shadow.camera.right = 200;
    //this.light2.shadow.radius        =  32;
    light2.shadow.mapSize.width = 128;
    light2.shadow.mapSize.height = 128;
    this.scene.add(light);
    this.scene.add(light2);

    // Create the Ground Grid; one line every 100 units
    const grid = new THREE.GridHelper(2000, 20, 0xcccccc, 0xcccccc);
    grid.position.y = -0.01;
    grid.material.opacity = 0.3;
    grid.material.transparent = true;
    this.scene.add(grid);

    this.camera.position.set(50, 100, 150);
    this.camera.lookAt(0, 45, 0);
    this.camera.updateProjectionMatrix();

    this.trackballControls = new THREE.TrackballControls(
      this.camera,
      renderer.domElement
    );
    // this.trackballControls.rotateSpeed = 0.5;
    // this.trackballControls.rotateSpeed = 2.0;
    // this.trackballControls.zoomSpeed = 1.2;
    // this.trackballControls.panSpeed = 0.8;
    // this.trackballControls.staticMoving = true;
    // this.trackballControls.dynamicDampingFactor = 0.3;

    renderer.render(this.scene, this.camera);

    renderer.setAnimationLoop(() => {
      this.trackballControls.update();
      renderer.render(this.scene, this.camera);
    });
  }
}

window.editor = new SegmentationEditor();

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  webgl2: false,
});

window.editor.render(renderer);

document.body.append(renderer.domElement);

window.addEventListener("resize", () => {
  window.editor.render(renderer);
});
