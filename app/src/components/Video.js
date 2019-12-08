//reference : https://nanonets.com/blog/object-detection-tensorflow-js/

import React, {Component} from 'react';
import "../css/Video.css";
import Row from 'react-bootstrap/Row';
import Button from 'react-bootstrap/Button';
import {getPredictions} from '../server/Server';
import {showDetections, drawImageProp} from '../common/Utility';

class Video extends Component {
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
    //console.log("in draw frame");
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
       if (this.videoRef.current.currentTime < this.videoRef.current.duration-1 && !this.paused) {
         setTimeout(() => {
           this.videoRef.current.play();
         }, 33)
       };
     });
    }

  }

  componentDidMount() {
    this.videoRef.current = document.createElement('video');
    this.videoRef.current.src = this.props.src;
    this.videoRef.current.onplay = this.drawFrame;
    this.videoRef.current.muted = true;

    //showing first frame of video
    this.videoRef.current.onloadeddata = () => {
      const ctx = this.canvasRef.current.getContext("2d");

      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
      drawImageProp(ctx, this.videoRef.current);
    }

  }

  startVideo = () => {
    this.paused = false;
    this.videoRef.current.play();

  }

  stopVideo = () => {
    fetch("http://localhost:5000/shutdown",{method:'POST'})
        .then(data => {})
    this.paused = true;
    this.videoRef.current.pause();

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
          <canvas ref={this.canvasRef} width="720px" height="500px"/>
          <canvas ref={this.bbCanvasRef} width="720px" height="500px"/>
        </Row>
      </div>



    );
  }
}

export default Video;
