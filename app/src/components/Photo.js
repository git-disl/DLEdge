//reference : https://nanonets.com/blog/object-detection-tensorflow-js/

import React, {Component} from 'react';
import "../css/Video.css";
import Row from 'react-bootstrap/Row';
import Button from 'react-bootstrap/Button';
import {getPredictions} from '../server/Server';
import {showDetections, drawImageProp} from '../common/Utility';

class Photo extends Component {
  canvasRef = React.createRef();
  bbCanvasRef = React.createRef();

  componentDidMount() {
    let image = new Image();

    image.src="";
    image.addEventListener("load", ()=> {

      const ctx = this.canvasRef.current.getContext("2d");

      drawImageProp(ctx, image);
    })
    image.src = this.props.src;


  }

  detectObjects = ()=>{
    this.getPredictionsFromServer();
  }

  getPredictionsFromServer = () => {

    this.canvasRef.current.toBlob(blob=>{
      let reader = new FileReader();
      reader.onload = file => {
        getPredictions(file.target.result, this.props.execution_mode, this.props.models, this.props.config)
             .then(data => {
               //don't want to show fps, so delete the key
               delete data.fps
               showDetections(data, this.bbCanvasRef.current);
             });
      }

      reader.readAsDataURL(blob);
    }, 'image/jpeg');

  }


  render() {
    return (
      <div className="fullHeight">
        <Row>
          <div>
            <Button className="controlBtn" onClick={this.detectObjects}>Detect Objects</Button>
          </div>
        </Row>
        <Row className="fullHeight frame">
            <canvas ref={this.canvasRef} width="720px" height="500px"/>
            <canvas ref={this.bbCanvasRef}  width="720px" height="500px" />
        </Row>
      </div>

    );
  }
}

export default Photo;
