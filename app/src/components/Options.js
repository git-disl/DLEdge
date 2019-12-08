import React, { Component } from "react";
import "../css/Options.css";
import Upload from './Upload';
import ObjectDetector from './ObjectDetector';
import Row from 'react-bootstrap/Row';
import ListGroup from 'react-bootstrap/ListGroup';

class Options extends Component {

  constructor() {
    super();
    this.state = {
      option:'',
      execution_mode:'',
      models: new Set()
    };
  }

  setOption = event => {
    this.setState({
      option: event.currentTarget.value
    });
  }

  startOver = () => {
    this.setState({option: ''});
  }

  render() {
    let option = this.state.option;
    if (option) {
      if (option === "upload") {
        return <Upload back={this.startOver}/>;
      } else {
        return <ObjectDetector type="webcam" back={this.startOver}/>;
      }
    } else {
      return (
          <Row className="viewArea">
              <ListGroup className="optionList">
                <ListGroup.Item action onClick={this.setOption} value="upload" className="rounded-circle option">
                  <i className="fa fa-file-video-o fa-4x" aria-hidden="true"></i>
                </ListGroup.Item>
                <ListGroup.Item action onClick={this.setOption} value="upload" className="rounded-circle option">
                  <i className="fa fa-file-image-o fa-4x" aria-hidden="true"></i>
                </ListGroup.Item>
                <ListGroup.Item action onClick={this.setOption} value="webcam" className="rounded-circle option">
                <i className="fa fa-video-camera fa-4x" aria-hidden="true"></i>
                </ListGroup.Item>
              </ListGroup>
          </Row>
      );
    }
  }
}

export default Options;
