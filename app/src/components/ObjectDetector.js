import React, { Component } from "react";
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import WebCam from './WebCam';
import Video from './Video';
import Photo from './Photo';
import Card from 'react-bootstrap/Card';
import CardDeck from 'react-bootstrap/CardDeck';
import modelOptions from '../config/modelOptions';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Loader from './Loader.js';
import '../css/ObjectDetector.css';


class ObjectDetector extends Component {
  constructor(props){
    super(props);

    this.state = {
      models: new Set(['tiny_yolov3_320']),
      config:{
        tiny_yolov3_320:{conf: '0.20', iou:'0.45'}
      },
      execution_mode: 'parallel',
      loading: false
    }
  }

  addModel = event => {
    const model = event.currentTarget.value;
    let models = this.state.models;
    let config = this.state.config;
    if (models.has(model)) {
      models.delete(model);
      delete config[model]
    } else {
      models.add(model);
      config[model] = {conf: '0.20', iou:'0.45'};
    }

    this.setState({
      models: models,
      config: config
    });

  }

  loadModels = ()=>{
    this.setState({
      loading: true
    });
    fetch('http://localhost:5000/reload_models?models='+Array.from(this.state.models).toString(),
          {method:'get'})
          .then(res => {
            this.setState({
              loading:false
            })
          });
  }

  updateConf = event => {
    let model = event.currentTarget.name;
    let config = this.state.config;
    config[model].conf = event.currentTarget.value;
    this.setState({
      config: config
    });
  }

  updateIOU = event => {
    let model = event.currentTarget.name;
    let config = this.state.config;
    config[model].iou = event.currentTarget.value;
    this.setState({
      config: config
    });
  }

  backButton= () =>{
    this.setState({
      models: new Set(['tiny_yolov3_320']),
      config:{
        tiny_yolov3_320:{conf: '0.20', iou:'0.45'}
      },
      execution_mode: 'parallel'
    });
    this.props.back();
  }

  render() {

    let showScreen = this.state.execution_mode && this.state.models.size!==0;

    let screen = null;
    if (showScreen) {
      if (this.props.type === "webcam") {
        screen = <WebCam execution_mode={this.state.execution_mode} models={this.state.models} config={this.state.config}/>;
      } else if (this.props.type === "video") {
        screen = <Video src={this.props.src} execution_mode={this.state.execution_mode} models={this.state.models} config={this.state.config}/>;
      } else {
        screen = <Photo src={this.props.src} execution_mode={this.state.execution_mode} models={this.state.models} config={this.state.config}/>
      }
    }


    return (
      <Container fluid={true}>
        <Row>
          <Button variant="link" onClick={this.backButton} className="backButton">
            <i className="fa fa-arrow-circle-left fa-2x" aria-hidden="true"></i>
          </Button>
        </Row>
        <Row>
          {this.state.loading? <Loader/> : null}
        </Row>
        <Row className="topRow">
          <Col md={3}>
            <CardDeck className="optionCards">
              <Card className="modelSelector">
                <Card.Header>Models</Card.Header>
                <Card.Body>
                  <Form>
                    {modelOptions.map(option => {
                      let extraOptions;
                      if (this.state.models.has(option.id)) {
                        extraOptions = (
                          <Row>
                            <Col>
                              <Form.Label >Conf:</Form.Label>
                              <Form.Control  as="input" type="text" name={option.id} value={this.state.config[option.id].conf} onChange={this.updateConf}/>
                            </Col>
                            <Col>
                              <Form.Label>IOU:</Form.Label>
                              <Form.Control  as="input" type="text" name={option.id} value={this.state.config[option.id].iou} onChange={this.updateIOU}/>
                            </Col>
                          </Row>
                        )
                      }
                      return (
                        <div id="modelOption" key={option.id}>
                          <Row>
                            <Form.Check
                              type="checkbox"
                              label={option.display_name}
                              id={option.id}
                              value = {option.id}
                              checked = {this.state.models.has(option.id)}
                              onChange = {this.addModel}
                            />
                          </Row>
                          {extraOptions}
                        </div>
                      );
                    })}
                  </Form>
                  <Button variant="link" onClick={this.loadModels} className="controlBtn">
                    Load Models
                  </Button>
                </Card.Body>
              </Card>
              <Card className="options">
                <Card.Header>Execution Mode</Card.Header>
                <Card.Body>
                  <Form>
                      <Form.Check
                        type="radio"
                        label="Parallel"
                        id="parallel"
                        value = "parallel"
                        checked = {this.state.execution_mode? this.state.execution_mode==="parallel" : false}
                        onChange = {()=>{this.setState({execution_mode: "parallel"})}}
                      />
                      <Form.Check
                        type="radio"
                        label="Ensemble"
                        id="ensemble"
                        value = "ensemble"
                        checked = {this.state.execution_mode? this.state.execution_mode==="ensemble" : false}
                        onChange = {()=>{this.setState({execution_mode: "ensemble"})}}
                      />
                  </Form>
                </Card.Body>
              </Card>
            </CardDeck>
          </Col>
          <Col md={7} className="screen">
            {showScreen? screen: null}
          </Col>
          <Col md={2} className="legend">
            {showScreen && this.state.execution_mode==="parallel"?
                (
                  Array.from(this.state.models).map(model => {

                    let modelInfo = modelOptions.filter(d => d.id === model)[0]
                    let color = modelInfo.color;
                    let name = modelInfo.display_name;
                    const styleObj = {
                      border: "2px solid " + color,
                      backgroundColor: color
                    }
                    return (<div key={name}>
                      <div className="box" style={styleObj}></div>
                      <div className="label" >{name}</div>
                    </div>)
                  })
                )
              : null}
          </Col>
        </Row>
      </Container>
    );
  }
}

export default ObjectDetector;
