import React, { Component } from "react";
import "../css/App.css";
import Options from './Options';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';

class App extends Component {
  render() {
    return (
        <Container fluid={true}>
          <Row className="main">
            <h1 className="main_title">Deep Learning on the Edge</h1>
          </Row>
            <Options/>
        </Container>
    );
  }
}

export default App;
