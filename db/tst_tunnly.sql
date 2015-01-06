-- phpMyAdmin SQL Dump
-- version 4.0.10deb1
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Jan 06, 2015 at 12:07 PM
-- Server version: 5.5.40-0ubuntu0.14.04.1
-- PHP Version: 5.5.9-1ubuntu4.5

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `tst_tunnly`
--

-- --------------------------------------------------------

--
-- Table structure for table `tunnly_ports`
--

CREATE TABLE IF NOT EXISTS `tunnly_ports` (
  `port_id` int(11) NOT NULL AUTO_INCREMENT,
  `port_dockerid` varchar(15) NOT NULL,
  `port_number` int(11) NOT NULL,
  `tunnly_code` varchar(16) NOT NULL,
  `port_proto` varchar(5) NOT NULL DEFAULT ' ',
  `port_timecreate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `port_active` tinyint(4) NOT NULL DEFAULT '1',
  PRIMARY KEY (`port_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=35 ;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
