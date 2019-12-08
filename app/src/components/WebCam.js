//reference : https://nanonets.com/blog/object-detection-tensorflow-js/
// reference: http://html5doctor.com/video-canvas-magic/

import React, {Component} from 'react';
import "../css/Video.css";
import Row from 'react-bootstrap/Row';
import Button from 'react-bootstrap/Button';
import {getPredictions} from '../server/Server';
import {showDetections, drawImageProp} from '../common/Utility';

class WebCam extends Component {
  videoRef = React.createRef();
  canvasRef = React.createRef();
  bbCanvasRef = React.createRef();

  constructor(props) {
    super(props);

    this.paused = false;
  }

  drawFrame = () => {
    if (!this.videoRef.current || !this.canvasRef.current) {
      this.videoRef.current.pause();
      return;
    }
    if(!this.paused) {
      this.videoRef.current.pause();
      const ctx = this.canvasRef.current.getContext("2d");
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
      drawImageProp(ctx, this.videoRef.current);

      this.canvasRef.current.toBlob(blob=>{
        let reader = new FileReader();
        reader.onload = file => {
          getPredictions(file.target.result, this.props.execution_mode, this.props.models, this.props.config)
               .then(data => {
                 if (!this.bbCanvasRef.current) {
                   return;
                 }
                 showDetections(data, this.bbCanvasRef.current);
               });
        }

        reader.readAsDataURL(blob);
      }, 'image/jpeg');
      requestAnimationFrame(()=>{
        if (this.videoRef.current.currentTime < this.videoRef.current.duration && !this.paused) {
          setTimeout(() => {
          this.videoRef.current.play();
        }, 33)
        }
      });
    }
  }

  startVideo = () => {
      this.paused = false;
      if (navigator.mediaDevices.getUserMedia) {
        // define a Promise that'll be used to load the webcam and read its frames
        navigator.mediaDevices
          .getUserMedia({
            video: true,
            audio: false,
          })
          .then(stream => {
            // pass the current frame to the window.stream
            window.stream = stream;
            // pass the stream to the videoRef
            this.videoRef.current = document.createElement('video');
            this.videoRef.current.srcObject = stream;
            this.videoRef.current.onplay = this.drawFrame;
            this.videoRef.current.muted = true;

            this.videoRef.current.onloadedmetadata = () => {
              this.videoRef.current.play();
            };

          }, (error) => {
            console.log("Couldn't start the webcam")
            console.error(error)
          });

      }
  }

  stopVideo = () => {
    fetch("http://localhost:5000/shutdown",{method:'POST'})
        .then(data => {})
    this.paused = true;
    window.stream.getTracks().forEach(track => track.stop())

  }

  render() {
    return (
      <div className="fullHeight">
        <Row>
          <div>
            <Button className="controlBtn" onClick={this.startVideo}>Start Detection</Button>
            <Button className="controlBtn" onClick={this.stopVideo}>Stop Detection</Button>
          </div>
        </Row>
        <Row className="fullHeight frame">
          <canvas ref={this.canvasRef} width="720" height="500"/>
          <canvas ref={this.bbCanvasRef} width="720" height="500"/>
        </Row>
      </div>
    );
  }
}

export default WebCam;
