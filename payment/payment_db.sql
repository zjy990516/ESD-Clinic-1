
CREATE DATABASE IF NOT EXISTS `treatment` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `treatment`;

CREATE TABLE `treatment` (
  `treatment_id` char(11) NOT NULL,
  `pet_id` char(32) NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `staff_id` int(11) NOT NULL,
  `price` float NOT NULL,
  `status` char(10) NOT NULL,
  PRIMARY KEY (`treatment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `medication` (
  `medication_id` char(11) NOT NULL,
  `treatment_id` char(11) NOT NULL,
  `pet_id` int(11) NOT NULL,
  `staff_id` char(13) NOT NULL,
  `status` int(11) NOT NULL,
  `description` char(100) DEFAULT NULL,
  `updatetime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`medication_id`),
  KEY `treatment_id` (`treatment_id`),
  CONSTRAINT `medication_ibfk_1` FOREIGN KEY (`treatment_id`) REFERENCES `treatment` (`treatment_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE DATABASE IF NOT EXISTS `payment` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `payment`;

-- --------------------------------------------------------

--
-- Table structure for table `books`
--

DROP TABLE IF EXISTS `payment`;
CREATE TABLE IF NOT EXISTS `payment` (
  `payment_id` integer(10) NOT NULL auto_increment,
  `treatment_id` char(11) NOT NULL,
  `payment_date` datetime NOT NULL,
  `payment_status` VARCHAR(10) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `paypal_id` char(20) NOT NULL,
  PRIMARY KEY (`payment_id`)
)ENGINE=InnoDB DEFAULT CHARSET=utf8;

